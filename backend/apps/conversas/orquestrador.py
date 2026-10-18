"""Orquestrador do assistente.

Ordem fixa de decisão (ver docs/architecture/ia-e-motor.md):

  1. Validação e escopo (conversa do próprio usuário; documento de contexto autorizado).
  2. Motor determinístico — regra publicada casou? Responde sem LLM.
  3. Busca híbrida restrita aos documentos que o usuário pode consultar.
  4. Sem evidência suficiente? Responde "sem fontes" + setores sugeridos (determinístico).
  5. RAG com o LLM local, em streaming, citando trechos [n].
  6. LLM indisponível? Resposta extrativa com os trechos encontrados.

As etapas 1–4 e a 6 são determinísticas. Só a etapa 5 envolve geração.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from asgiref.sync import sync_to_async
from django.conf import settings

from apps.acesso.models import Acao
from apps.acesso.servico import pode
from apps.auditoria.servico import registrar
from apps.busca.servico import buscar_trechos, evidencia_suficiente
from apps.ia.provedores import ProvedorIndisponivel, obter_provedor
from apps.ia.rag import FRASE_SEM_RESPOSTA, TrechoContexto, citacoes_validas, montar_mensagens
from apps.motor.motor import avaliar, renderizar
from apps.organizacao.diretorio import sugerir_setores

from .models import Confianca, Conversa, Mensagem, Origem

TAMANHO_MAXIMO_PERGUNTA = 4000

Emissor = Callable[[dict], Awaitable[None]]


class ErroConversa(Exception):
    def __init__(self, codigo: str, mensagem: str):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


@dataclass
class Plano:
    tipo: str  # "pronta" | "gerar"
    origem: str = ""
    confianca: str = ""
    conteudo: str = ""
    etapas: list = field(default_factory=list)
    setor: dict | None = None
    setores_sugeridos: list = field(default_factory=list)
    sugestoes: list = field(default_factory=list)
    fontes: list = field(default_factory=list)
    trechos: list[TrechoContexto] = field(default_factory=list)
    mensagens_llm: list[dict] = field(default_factory=list)
    rastro: dict = field(default_factory=dict)


def _setores_dados(pergunta: str, usuario) -> list[dict]:
    dados = []
    for s in sugerir_setores(pergunta):
        setor = s.setor
        dados.append(
            {
                "id": setor.id,
                "sigla": setor.sigla,
                "nome": setor.nome,
                "descricao": setor.descricao,
                "canal_contato": setor.canal_contato
                if setor.contato_visivel_para_todos or usuario.setor_id == setor.id
                else None,
                "horario_atendimento": setor.horario_atendimento,
                "orientacao_acesso": setor.orientacao_acesso,
                "pontuacao": s.pontuacao,
            }
        )
    return dados


def _fonte_de_trecho(t: TrechoContexto, documento, usuario, citada: bool, texto_trecho: str) -> dict:
    return {
        "numero": t.numero,
        "documento_id": t.documento_id,
        "trecho_id": t.trecho_id,
        "titulo": t.titulo,
        "tipo_arquivo": documento.tipo_arquivo,
        "pagina": t.pagina,
        "secao": t.secao,
        "trecho": texto_trecho[:600],
        "versao": documento.versao,
        "vigencia": documento.vigencia,
        "atualizado_em": documento.atualizado_em.isoformat(),
        "pode_abrir": pode(usuario, Acao.VISUALIZAR, documento),
        "citada": citada,
        "similaridade": t.pontuacao,
    }


def obter_conversa(usuario, conversa_id: int | None, documento_id: int | None, pergunta: str) -> Conversa:
    if conversa_id:
        conversa = Conversa.objects.filter(pk=conversa_id, usuario=usuario).first()
        if not conversa:  # conversa de outro usuário é tratada como inexistente
            raise ErroConversa("conversa_inexistente", "Conversa não encontrada.")
        return conversa
    documento = None
    if documento_id:
        from apps.documentos.models import Documento

        documento = Documento.objects.filter(pk=documento_id).first()
        if not documento or not pode(usuario, Acao.CONSULTAR, documento):
            raise ErroConversa("documento_indisponivel", "Documento indisponível para o seu perfil.")
    titulo = " ".join(pergunta.split())[:80] or "Nova conversa"
    return Conversa.objects.create(usuario=usuario, titulo=titulo, documento_contexto=documento)


def preparar(usuario, conversa: Conversa, pergunta: str) -> Plano:
    rastro: dict = {"etapas": []}

    documento = conversa.documento_contexto
    if documento is not None and not pode(usuario, Acao.CONSULTAR, documento):
        raise ErroConversa("documento_indisponivel", "Documento indisponível para o seu perfil atual.")

    # 2. Motor determinístico (não se aplica a conversas restritas a um documento)
    if documento is None:
        resultado = avaliar(pergunta, usuario)
        rastro["motor"] = resultado.rastro
        rastro["etapas"].append(f"motor:{resultado.decisao}")
        if resultado.decisao == "responder":
            r = renderizar(resultado.regra, usuario)
            rastro["regra"] = {"codigo": resultado.regra.codigo, "versao": resultado.regra.versao}
            if r.get("fonte_revogada"):
                rastro["aviso"] = "fonte da regra revogada"
            return Plano(
                tipo="pronta",
                origem=Origem.DETERMINISTICO,
                confianca=Confianca.CAUTELA if r.get("fonte_revogada") else Confianca.VERIFICADA,
                conteudo=r["conteudo"],
                etapas=r["etapas"],
                setor=r["setor"],
                fontes=r["fontes"],
                rastro=rastro,
            )
        if resultado.decisao == "desambiguar":
            return Plano(
                tipo="pronta",
                origem=Origem.DESAMBIGUACAO,
                confianca=Confianca.VERIFICADA,
                conteudo="Encontrei mais de um assunto relacionado à sua pergunta. Qual deles você procura?",
                sugestoes=[
                    (c.regra.frases_exemplo[0] if c.regra.frases_exemplo else c.regra.titulo)
                    for c in resultado.alternativas
                ],
                rastro=rastro,
            )

    # 3. Busca híbrida com filtro de permissões
    limite = settings.NEXO_IA["CONTEXTO_MAX_TRECHOS"]
    resultados, diagnostico = buscar_trechos(
        usuario, pergunta, documento_id=documento.id if documento else None, limite=limite * 2
    )
    rastro["busca"] = diagnostico
    rastro["etapas"].append(f"busca:{len(resultados)}")

    if not resultados or not evidencia_suficiente(resultados):
        rastro["etapas"].append("sem_evidencia")
        setores = _setores_dados(pergunta, usuario)
        conteudo = "Não encontrei fontes suficientes nos documentos disponíveis para o seu perfil para responder com segurança."
        if setores:
            conteudo += " Estes setores podem ajudar com o assunto:"
        else:
            conteudo += " Tente reformular a pergunta ou consulte o diretório de setores."
        return Plano(
            tipo="pronta",
            origem=Origem.SEM_FONTES,
            confianca=Confianca.CAUTELA,
            conteudo=conteudo,
            setores_sugeridos=setores,
            rastro=rastro,
        )

    trechos = [
        TrechoContexto(
            numero=i,
            trecho_id=r.trecho.id,
            documento_id=r.trecho.documento_id,
            titulo=r.trecho.documento.titulo,
            pagina=r.trecho.pagina,
            secao=r.trecho.secao,
            texto=r.trecho.texto,
            pontuacao=r.similaridade if r.similaridade is not None else round(r.pontuacao, 4),
        )
        for i, r in enumerate(resultados[:limite], start=1)
    ]
    historico = [
        {"role": "user" if m.papel == Mensagem.Papel.USUARIO else "assistant", "content": m.conteudo}
        for m in conversa.mensagens.order_by("-id")[1:7]
    ][::-1]
    return Plano(
        tipo="gerar",
        origem=Origem.RAG,
        trechos=trechos,
        mensagens_llm=montar_mensagens(pergunta, trechos, historico),
        rastro=rastro,
    )


def _conteudo_extrativo(trechos: list[TrechoContexto]) -> str:
    linhas = [
        "O serviço de geração de respostas está indisponível no momento. "
        "Estes são os trechos mais relevantes dos documentos autorizados para o seu perfil:",
        "",
    ]
    for t in trechos[:4]:
        resumo = " ".join(t.texto.split())[:320]
        linhas.append(f"- {resumo}… [{t.numero}]")
    return "\n".join(linhas)


def finalizar(
    usuario,
    conversa: Conversa,
    pergunta: str,
    plano: Plano,
    gerado: str = "",
    *,
    interrompida: bool = False,
    extrativo: bool = False,
    inicio: float | None = None,
) -> Mensagem:
    from apps.documentos.models import Documento

    if plano.tipo == "gerar":
        if extrativo:
            plano.origem = Origem.EXTRATIVO
            plano.confianca = Confianca.CAUTELA
            gerado = _conteudo_extrativo(plano.trechos)
        conteudo, citados = citacoes_validas(gerado, len(plano.trechos))
        documentos = Documento.objects.in_bulk({t.documento_id for t in plano.trechos})
        plano.fontes = [
            _fonte_de_trecho(t, documentos[t.documento_id], usuario, t.numero in citados, t.texto)
            for t in plano.trechos
            if t.documento_id in documentos
        ]
        plano.conteudo = conteudo.strip()
        plano.rastro["citacoes"] = citados
        if not extrativo:
            if FRASE_SEM_RESPOSTA.lower() in conteudo.lower():
                plano.origem = Origem.SEM_FONTES
                plano.confianca = Confianca.CAUTELA
                plano.setores_sugeridos = _setores_dados(pergunta, usuario)
                plano.fontes = [f for f in plano.fontes if f["citada"]]
            elif citados:
                plano.confianca = Confianca.FUNDAMENTADA
            else:
                plano.confianca = Confianca.CAUTELA
                plano.rastro["aviso"] = "resposta sem citações explícitas"

    mensagem = Mensagem.objects.create(
        conversa=conversa,
        papel=Mensagem.Papel.ASSISTENTE,
        conteudo=plano.conteudo or "(resposta interrompida)",
        origem=plano.origem,
        confianca=plano.confianca,
        etapas=plano.etapas,
        setor=plano.setor,
        setores_sugeridos=plano.setores_sugeridos,
        sugestoes=plano.sugestoes,
        fontes=plano.fontes,
        rastro=plano.rastro,
        interrompida=interrompida,
        duracao_ms=int((time.monotonic() - inicio) * 1000) if inicio else None,
    )
    conversa.save(update_fields=["atualizada_em"])
    registrar(
        None,
        "CONSULTA_ASSISTENTE",
        usuario=usuario,
        objeto=conversa,
        detalhes={
            "origem": plano.origem,
            "regra": (plano.rastro.get("regra") or {}).get("codigo"),
            "documentos": sorted({f["documento_id"] for f in plano.fontes}),
            "tamanho_pergunta": len(pergunta),
            "interrompida": interrompida,
        },
    )
    return mensagem


def registrar_pergunta(conversa: Conversa, pergunta: str) -> Mensagem:
    return Mensagem.objects.create(conversa=conversa, papel=Mensagem.Papel.USUARIO, conteudo=pergunta)


async def executar(
    usuario,
    conversa_id: int | None,
    pergunta: str,
    emitir: Emissor,
    documento_id: int | None = None,
    cancelado: Callable[[], bool] = lambda: False,
) -> Mensagem:
    """Fluxo completo com eventos de progresso (usado pelo WebSocket e pela API REST)."""
    from .serializers import MensagemSerializer

    inicio = time.monotonic()
    pergunta = (pergunta or "").strip()
    if not pergunta:
        raise ErroConversa("pergunta_vazia", "Digite uma pergunta.")
    if len(pergunta) > TAMANHO_MAXIMO_PERGUNTA:
        raise ErroConversa("pergunta_longa", f"A pergunta deve ter até {TAMANHO_MAXIMO_PERGUNTA} caracteres.")

    conversa = await sync_to_async(obter_conversa)(usuario, conversa_id, documento_id, pergunta)
    await emitir({"tipo": "conversa", "id": conversa.id, "titulo": conversa.titulo})
    pergunta_msg = await sync_to_async(registrar_pergunta)(conversa, pergunta)
    await emitir({"tipo": "pergunta_registrada", "id": pergunta_msg.id})

    await emitir({"tipo": "status", "etapa": "analisando", "texto": "Analisando a pergunta"})
    plano = await sync_to_async(preparar)(usuario, conversa, pergunta)

    gerado, interrompida, extrativo = "", False, False
    if plano.tipo == "gerar":
        await emitir(
            {
                "tipo": "status",
                "etapa": "consultando_fontes",
                "texto": f"Consultando {len(plano.trechos)} trechos autorizados",
            }
        )
        await emitir({"tipo": "status", "etapa": "gerando", "texto": "Gerando resposta"})
        provedor = obter_provedor()
        partes: list[str] = []
        try:
            async for pedaco in provedor.gerar_stream(plano.mensagens_llm):
                if cancelado():
                    interrompida = True
                    break
                partes.append(pedaco)
                await emitir({"tipo": "token", "texto": pedaco})
        except ProvedorIndisponivel:
            extrativo = True
            await emitir(
                {
                    "tipo": "aviso",
                    "codigo": "ia_indisponivel",
                    "texto": "Serviço de IA indisponível. Exibindo os trechos mais relevantes.",
                }
            )
        gerado = "".join(partes)

    mensagem = await sync_to_async(finalizar)(
        usuario, conversa, pergunta, plano, gerado, interrompida=interrompida, extrativo=extrativo, inicio=inicio
    )
    dados = await sync_to_async(lambda: MensagemSerializer(mensagem, context={"usuario": usuario}).data)()
    await emitir({"tipo": "resposta", "conversa_id": conversa.id, "mensagem": dados})
    return mensagem
