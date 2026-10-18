"""Motor determinístico de respostas.

Primeira camada do assistente: antes de qualquer busca vetorial ou LLM, a
pergunta é comparada com as regras publicadas. Se uma regra casa com
pontuação suficiente, a resposta curada é devolvida exatamente como foi
aprovada, com suas fontes — sem geração.

Propriedades garantidas (cobertas por testes):
- Mesma pergunta + mesmo conjunto de regras ⇒ mesmo resultado.
- Ordenação total: pontuação desc, prioridade desc, código asc.
- Todo resultado carrega um rastro explicando a decisão.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.acesso.models import Acao
from apps.acesso.servico import pode
from apps.comum import texto

from .models import Regra, StatusRegra

PESO_EXEMPLOS = 0.75
PESO_PALAVRAS = 0.25
PESO_CONTENCAO = 0.85


@dataclass
class Candidato:
    regra: Regra
    pontuacao: float
    componentes: dict

    def resumo(self) -> dict:
        return {
            "codigo": self.regra.codigo,
            "titulo": self.regra.titulo,
            "pontuacao": self.pontuacao,
            **self.componentes,
        }


@dataclass
class ResultadoMotor:
    decisao: str  # "responder" | "desambiguar" | "nao_aplicavel"
    regra: Regra | None = None
    pontuacao: float = 0.0
    alternativas: list[Candidato] = field(default_factory=list)
    rastro: dict = field(default_factory=dict)


def _termos_presentes(termo: str, tokens_pergunta: set[str]) -> bool:
    alvo = texto.tokens(termo)
    return bool(alvo) and all(t in tokens_pergunta for t in alvo)


def regras_aplicaveis(usuario, hoje: date | None = None):
    hoje = hoje or timezone.localdate()
    qs = Regra.objects.filter(status=StatusRegra.PUBLICADA).filter(
        Q(vigencia_inicio__isnull=True) | Q(vigencia_inicio__lte=hoje),
        Q(vigencia_fim__isnull=True) | Q(vigencia_fim__gte=hoje),
    )
    regras = []
    perfis = set(usuario.perfis.values_list("id", flat=True)) if usuario else set()
    for regra in qs.prefetch_related("setores_alvo", "perfis_alvo").select_related("setor_responsavel"):
        setores_alvo = {s.id for s in regra.setores_alvo.all()}
        perfis_alvo = {p.id for p in regra.perfis_alvo.all()}
        if setores_alvo and (not usuario or usuario.setor_id not in setores_alvo):
            continue
        if perfis_alvo and not (perfis_alvo & perfis):
            continue
        regras.append(regra)
    return regras


def pontuar(regra: Regra, pergunta: str, tokens_pergunta: list[str]) -> Candidato | None:
    conjunto = set(tokens_pergunta)
    for termo in regra.termos_excludentes or []:
        if _termos_presentes(termo, conjunto):
            return None
    for termo in regra.termos_obrigatorios or []:
        if not _termos_presentes(termo, conjunto):
            return None

    normalizada = texto.normalizar(pergunta)
    for padrao in regra.padroes_regex or []:
        try:
            if re.search(padrao, normalizada, flags=re.IGNORECASE):
                return Candidato(regra, 1.0, {"criterio": "regex", "padrao": padrao})
        except re.error:
            continue

    melhor_exemplo, similaridade = "", 0.0
    for exemplo in regra.frases_exemplo or []:
        tokens_exemplo = texto.tokens(exemplo)
        s = texto.dice(tokens_pergunta, tokens_exemplo)
        # Pergunta que contém todos os termos de um exemplo (com 2+ termos) é forte indício,
        # mesmo que traga palavras a mais.
        if len(tokens_exemplo) >= 2:
            s = max(s, PESO_CONTENCAO * texto.cobertura(tokens_exemplo, tokens_pergunta))
        if s > similaridade:
            melhor_exemplo, similaridade = exemplo, s

    vocabulario = set()
    for palavra in regra.palavras_chave or []:
        vocabulario.update(texto.tokens(palavra))
    comuns = conjunto & vocabulario
    reforco = len(comuns) / max(1, min(len(vocabulario), len(conjunto))) if vocabulario else 0.0

    pontuacao = round(PESO_EXEMPLOS * similaridade + PESO_PALAVRAS * reforco, 4)
    if pontuacao <= 0:
        return None
    return Candidato(
        regra,
        pontuacao,
        {
            "criterio": "similaridade",
            "similaridade_exemplo": round(similaridade, 4),
            "exemplo_mais_proximo": melhor_exemplo,
            "palavras_chave_encontradas": sorted(comuns),
        },
    )


def avaliar(pergunta: str, usuario=None, regras: list[Regra] | None = None) -> ResultadoMotor:
    cfg = settings.NEXO_MOTOR
    limiar, margem = cfg["LIMIAR"], cfg["MARGEM_AMBIGUIDADE"]
    tokens_pergunta = texto.tokens(pergunta)
    rastro = {
        "pergunta_normalizada": texto.normalizar(pergunta),
        "tokens": tokens_pergunta,
        "limiar": limiar,
        "margem_ambiguidade": margem,
    }
    if not tokens_pergunta:
        rastro["motivo"] = "pergunta sem termos significativos"
        return ResultadoMotor("nao_aplicavel", rastro=rastro)

    candidatos = []
    for regra in regras if regras is not None else regras_aplicaveis(usuario):
        candidato = pontuar(regra, pergunta, tokens_pergunta)
        if candidato:
            candidatos.append(candidato)
    candidatos.sort(key=lambda c: (-c.pontuacao, -c.regra.prioridade, c.regra.codigo))
    rastro["candidatos"] = [c.resumo() for c in candidatos[:5]]

    acima = [c for c in candidatos if c.pontuacao >= limiar]
    if not acima:
        rastro["motivo"] = "nenhuma regra atingiu o limiar"
        return ResultadoMotor("nao_aplicavel", rastro=rastro)

    primeiro = acima[0]
    empatados = [c for c in acima[1:] if primeiro.pontuacao - c.pontuacao < margem and c.pontuacao < 1.0]
    if empatados and primeiro.pontuacao < 1.0 and primeiro.regra.prioridade == empatados[0].regra.prioridade:
        rastro["motivo"] = "regras com pontuação muito próxima; pedindo desambiguação"
        return ResultadoMotor("desambiguar", alternativas=[primeiro, *empatados][:3], rastro=rastro)

    rastro["motivo"] = f"regra {primeiro.regra.codigo} selecionada"
    rastro["regra_versao"] = primeiro.regra.versao
    return ResultadoMotor("responder", regra=primeiro.regra, pontuacao=primeiro.pontuacao, rastro=rastro)


def _substituir(modelo: str, usuario) -> str:
    valores = {
        "{usuario_nome}": usuario.nome_completo if usuario else "",
        "{setor_usuario}": usuario.setor.nome if usuario and usuario.setor_id else "seu setor",
    }
    for chave, valor in valores.items():
        modelo = modelo.replace(chave, valor)
    return modelo


def renderizar(regra: Regra, usuario) -> dict:
    """Monta a resposta da regra respeitando as permissões do usuário."""
    todas = list(regra.fontes.select_related("documento", "documento__setor_responsavel"))
    fontes = []
    for fonte in todas:
        doc = fonte.documento
        if not pode(usuario, Acao.CONSULTAR, doc):
            continue
        fontes.append(
            {
                "documento_id": doc.id,
                "titulo": doc.titulo,
                "tipo_arquivo": doc.tipo_arquivo,
                "pagina": fonte.pagina,
                "secao": fonte.secao,
                "trecho": fonte.trecho_citado,
                "versao": doc.versao,
                "vigencia": doc.vigencia,
                "atualizado_em": doc.atualizado_em.isoformat(),
                "pode_abrir": pode(usuario, Acao.VISUALIZAR, doc),
                "citada": True,
            }
        )

    setor = regra.setor_responsavel
    setor_dados = (
        {
            "id": setor.id,
            "sigla": setor.sigla,
            "nome": setor.nome,
            "canal_contato": setor.canal_contato
            if setor.contato_visivel_para_todos or (usuario and usuario.setor_id == setor.id)
            else None,
            "horario_atendimento": setor.horario_atendimento,
            "orientacao_acesso": setor.orientacao_acesso,
        }
        if setor
        else None
    )

    if todas and not fontes:
        # O fundamento não é acessível a este perfil: só o encaminhamento é apresentado.
        conteudo = (
            "A orientação completa sobre este assunto está em documentação que não está "
            "disponível para o seu perfil de acesso."
        )
        if setor:
            conteudo += f"\n\nProcure **{setor.nome} ({setor.sigla})**"
            conteudo += f" — {setor_dados['canal_contato']}." if setor_dados["canal_contato"] else "."
            if setor.orientacao_acesso:
                conteudo += f"\n\n{setor.orientacao_acesso}"
        return {"conteudo": conteudo, "etapas": [], "setor": setor_dados, "fontes": [], "modo": "somente_roteamento"}

    conteudo = _substituir(regra.resposta, usuario).replace("{setor_responsavel}", setor.nome if setor else "")
    revogadas = [f for f in todas if f.documento.vigencia == "revogado" and pode(usuario, Acao.CONSULTAR, f.documento)]
    if revogadas:
        # A regra continua respondendo até a gestão revisá-la, mas avisa que o fundamento foi revogado (ADR-015).
        quando = revogadas[0].documento.revogado_em
        conteudo += (
            "\n\n> **Atenção:** o documento que fundamenta esta resposta foi revogado"
            + (f" em {quando.strftime('%d/%m/%Y')}" if quando else "")
            + ". Confirme a orientação com o setor responsável antes de seguir."
        )
    return {
        "fonte_revogada": bool(revogadas),
        "conteudo": conteudo,
        "etapas": [{"titulo": e.get("titulo", ""), "descricao": e.get("descricao", "")} for e in (regra.etapas or [])],
        "setor": setor_dados,
        "fontes": fontes,
        "modo": "completo",
    }
