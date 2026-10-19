"""Memória da conversa por compactação (ADR-021).

O assistente recebe literalmente só as mensagens recentes da conversa (NEXO_MEMORIA_JANELA). As anteriores
são **compactadas** num resumo guardado na própria conversa, para que perguntas de continuação
("e o prazo?", "e para servidor cedido?") sejam entendidas sem mandar a conversa inteira ao LLM.

Decisões (ver ADR-021):
- a memória é **da conversa**: nada passa de uma conversa para outra nem de uma pessoa para outra;
- a compactação é **determinística**: guarda a pergunta (encurtada), a origem da resposta e os documentos
  citados; **não copia o texto das respostas** (que pode conter trechos de documentos) e não usa o LLM,
  que fica livre para responder (ADR-020);
- os títulos dos documentos citados são resolvidos **na hora do uso**, pelo motor de permissões (ADR-005):
  documento que a pessoa deixou de poder consultar some do resumo;
- o resumo serve só para entender a pergunta; não é fonte e não pode ser citado;
- apagar a conversa apaga a memória (mesmo registro).
"""

from __future__ import annotations

import re

from django.conf import settings

from apps.acesso.models import Acao
from apps.acesso.servico import pode
from apps.comum import texto

from .models import Conversa, Mensagem

VERSAO = 1
TAMANHO_PERGUNTA = 240
# Pergunta que só faz sentido com a anterior: começa com "e …", "mas …", "quanto a …", "nesse caso …"
# ou retoma o assunto com "isso", "disso", "dele" etc.
_CONTINUACAO = re.compile(r"^\s*(e|mas|quanto\s+ao?|nesse\s+caso|neste\s+caso|no\s+caso)(?=[\s,?])", re.I)
_RETOMADA = re.compile(r"\b(isso|disso|nisso|dele|dela|deles|delas)\b", re.I)  # "nesta semana" não é retomada


def _encurtar(conteudo: str) -> str:
    plano = " ".join(conteudo.split())
    return plano if len(plano) <= TAMANHO_PERGUNTA else plano[: TAMANHO_PERGUNTA - 1].rstrip() + "…"


def _documentos_citados(mensagem: dict) -> list[int]:
    ids = [f.get("documento_id") for f in mensagem.get("fontes") or [] if f.get("citada", True)]
    return list(dict.fromkeys(i for i in ids if isinstance(i, int)))


def atualizar(conversa: Conversa, manter: int | None = None) -> bool:
    """Compacta as mensagens anteriores às `manter` mais recentes. Devolve True se a memória mudou."""
    cfg = settings.NEXO_MEMORIA
    manter = cfg["JANELA_RECENTE"] if manter is None else manter  # as mesmas que vão literais ao LLM
    memoria = conversa.memoria or {}
    ate = memoria.get("ate_id", 0)
    pendentes = list(
        conversa.mensagens.filter(id__gt=ate)
        .order_by("id")
        .values("id", "papel", "conteudo", "origem", "fontes", "rastro")
    )
    compactar = pendentes[: max(0, len(pendentes) - manter)]
    if not compactar:
        return False

    itens = [dict(i) for i in memoria.get("itens", [])]
    for m in compactar:
        if m["papel"] == Mensagem.Papel.USUARIO:
            itens.append({"pergunta": _encurtar(m["conteudo"]), "origem": "", "documentos": [], "regra": None})
        elif itens and not itens[-1]["origem"]:
            itens[-1]["origem"] = m["origem"] or "?"
            itens[-1]["documentos"] = _documentos_citados(m)
            itens[-1]["regra"] = ((m["rastro"] or {}).get("regra") or {}).get("codigo")

    maximo = cfg["MAXIMO_ITENS"]
    conversa.memoria = {
        "versao": VERSAO,
        "ate_id": compactar[-1]["id"],
        "compactadas": memoria.get("compactadas", 0) + len(compactar),
        "descartadas": memoria.get("descartadas", 0) + max(0, len(itens) - maximo),
        "itens": itens[-maximo:],
    }
    conversa.save(update_fields=["memoria"])
    return True


def texto_para_ia(conversa: Conversa, usuario) -> str:
    """Resumo pronto para o contexto do LLM, com as permissões de agora. Vazio se não houver memória."""
    from apps.documentos.models import Documento

    itens = (conversa.memoria or {}).get("itens") or []
    if not itens:
        return ""
    ids = {i for item in itens for i in item.get("documentos", [])}
    documentos = Documento.objects.in_bulk(ids) if ids else {}
    visiveis = {i: d.titulo for i, d in documentos.items() if pode(usuario, Acao.CONSULTAR, d)}
    linhas = []
    for item in itens:
        linha = f"- O servidor perguntou: {item['pergunta']}"
        titulos = [visiveis[i] for i in item.get("documentos", []) if i in visiveis]
        if titulos:
            linha += f" (respondido com: {'; '.join(titulos)})"
        elif item.get("origem") == "sem_fontes":
            linha += " (não havia fontes suficientes)"
        linhas.append(linha)
    return "\n".join(linhas)


def pergunta_para_busca(conversa: Conversa, pergunta: str) -> tuple[str, bool]:
    """Pergunta de continuação ("e o prazo?") é buscada junto com a pergunta anterior da conversa."""
    if not (_CONTINUACAO.match(pergunta) or (_RETOMADA.search(pergunta) and len(texto.tokens(pergunta)) <= 6)):
        return pergunta, False
    anterior = (
        conversa.mensagens.filter(papel=Mensagem.Papel.USUARIO).order_by("-id").values_list("conteudo", flat=True)[1:2]
    )
    if not anterior:
        return pergunta, False
    return f"{_encurtar(anterior[0])} {pergunta}", True


def resumo_publico(conversa: Conversa) -> dict:
    """O que a pessoa vê sobre a memória da própria conversa."""
    memoria = conversa.memoria or {}
    return {"mensagens_compactadas": memoria.get("compactadas", 0), "itens": len(memoria.get("itens") or [])}
