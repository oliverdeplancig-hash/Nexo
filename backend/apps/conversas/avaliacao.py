"""Avaliação da qualidade das respostas do assistente (ADR-025).

Um **conjunto de avaliação** é um arquivo JSON com perguntas de referência sobre o acervo e o que se espera de
cada resposta. O avaliador faz as perguntas pelo mesmo caminho do chat (motor determinístico, busca com
permissões, IA), como um usuário real, e mede:

- **fonte**: algum dos documentos esperados aparece entre as fontes citadas (ou consultadas, nas respostas só
  com trechos) — e em que posição;
- **conteúdo**: a resposta traz os termos obrigatórios e nenhum dos proibidos (sem acento nem maiúsculas);
- **recusa**: perguntas fora do acervo devem dar "sem fontes" em vez de inventar;
- **origem**: quando o caso indica (ex.: deve ser respondida por regra do motor);
- tempo de resposta.

Formato (exemplo em `backend/avaliacao/exemplo-demonstracao.json`):

    {"nome": "...", "usuario": "servidor.demo",
     "casos": [{"id": "ferias-1", "pergunta": "Como solicito férias?",
                "fontes": ["solicitação de férias"], "contem": ["30 dias"], "nao_contem": [],
                "origem": "deterministico", "sem_resposta": false, "tema": "Pessoal"}]}

Conjuntos com documentos reais da instituição ficam FORA do Git (pasta `backend/avaliacao/local/`).
"""

from __future__ import annotations

import json
import statistics
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

from asgiref.sync import async_to_sync

from .models import Conversa, Origem


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


@dataclass
class Caso:
    id: str
    pergunta: str
    fontes: list[str] = field(default_factory=list)
    contem: list[str] = field(default_factory=list)
    nao_contem: list[str] = field(default_factory=list)
    origem: str = ""
    sem_resposta: bool = False
    tema: str = ""


@dataclass
class Resultado:
    id: str
    pergunta: str
    tema: str
    origem: str
    fonte_ok: bool | None
    posicao_fonte: int | None
    conteudo_ok: bool | None
    evidencia_ok: bool | None
    faltaram: list[str]
    proibidos: list[str]
    recusa_ok: bool | None
    origem_ok: bool | None
    segundos: float
    fontes_citadas: list[str]
    resposta: str

    @property
    def aprovado(self) -> bool:
        return all(v is not False for v in (self.fonte_ok, self.conteudo_ok, self.recusa_ok, self.origem_ok))


def carregar(caminho: str | Path) -> tuple[dict, list[Caso]]:
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    campos = set(Caso.__dataclass_fields__)
    casos = [Caso(**{k: v for k, v in c.items() if k in campos}) for c in dados.get("casos", [])]
    ids = [c.id for c in casos]
    if len(ids) != len(set(ids)):
        raise ValueError("Há casos com o mesmo id no conjunto de avaliação.")
    return dados, casos


def _perguntar(usuario, pergunta: str):
    from .orquestrador import executar

    async def _sem_eventos(_evento):
        return None

    return async_to_sync(executar)(usuario, None, pergunta, _sem_eventos)


def avaliar_caso(usuario, caso: Caso) -> Resultado:
    inicio = time.monotonic()
    mensagem = _perguntar(usuario, caso.pergunta)
    segundos = time.monotonic() - inicio
    fontes = mensagem.fontes or []
    extrativa = mensagem.origem == Origem.EXTRATIVO
    citadas = [f.get("titulo", "") for f in fontes if f.get("citada", True) or extrativa]
    texto = normalizar(mensagem.conteudo)

    fonte_ok = posicao = None
    if caso.fontes and not caso.sem_resposta:
        esperadas = [normalizar(f) for f in caso.fontes]
        posicoes = [i for i, t in enumerate(citadas, start=1) if any(e in normalizar(t) for e in esperadas)]
        fonte_ok, posicao = bool(posicoes), (posicoes[0] if posicoes else None)

    # Evidência: os termos esperados estão nos trechos entregues à IA? Mede a busca sem depender do modelo.
    from apps.documentos.models import Trecho

    ids = [f["trecho_id"] for f in fontes if f.get("trecho_id")]
    completos = dict(Trecho.objects.filter(id__in=ids).values_list("id", "texto"))
    trechos = normalizar(" ".join(completos.get(f.get("trecho_id"), f.get("trecho", "")) for f in fontes))
    sem_busca = mensagem.origem in (Origem.DETERMINISTICO, Origem.DESAMBIGUACAO)  # regra do motor: não há trechos
    evidencia_ok = (
        None
        if not caso.contem or caso.sem_resposta or sem_busca
        else all(normalizar(t) in trechos for t in caso.contem)
    )
    faltaram = [t for t in caso.contem if normalizar(t) not in texto]
    proibidos = [t for t in caso.nao_contem if normalizar(t) in texto]
    conteudo_ok = None if not (caso.contem or caso.nao_contem) else not faltaram and not proibidos
    recusa_ok = (mensagem.origem == Origem.SEM_FONTES) if caso.sem_resposta else None
    origem_ok = (mensagem.origem == caso.origem) if caso.origem else None

    Conversa.objects.filter(pk=mensagem.conversa_id).delete()  # a avaliação não deixa conversas no histórico
    return Resultado(
        id=caso.id,
        pergunta=caso.pergunta,
        tema=caso.tema,
        origem=mensagem.origem,
        fonte_ok=fonte_ok,
        posicao_fonte=posicao,
        conteudo_ok=conteudo_ok,
        evidencia_ok=evidencia_ok,
        faltaram=faltaram,
        proibidos=proibidos,
        recusa_ok=recusa_ok,
        origem_ok=origem_ok,
        segundos=round(segundos, 2),
        fontes_citadas=citadas[:5],
        resposta=mensagem.conteudo,
    )


def _taxa(valores: list[bool | None]) -> dict:
    validos = [v for v in valores if v is not None]
    return {
        "acertos": sum(validos),
        "total": len(validos),
        "taxa": round(sum(validos) / len(validos), 3) if validos else None,
    }


def resumir(resultados: list[Resultado]) -> dict:
    tempos = [r.segundos for r in resultados]
    posicoes = [r.posicao_fonte for r in resultados if r.posicao_fonte]
    return {
        "casos": len(resultados),
        "aprovados": _taxa([r.aprovado for r in resultados]),
        "fonte": _taxa([r.fonte_ok for r in resultados]),
        "fonte_em_primeiro": _taxa([(r.posicao_fonte == 1) if r.fonte_ok is not None else None for r in resultados]),
        "conteudo": _taxa([r.conteudo_ok for r in resultados]),
        "evidencia": _taxa([r.evidencia_ok for r in resultados]),
        "recusa": _taxa([r.recusa_ok for r in resultados]),
        "origem": _taxa([r.origem_ok for r in resultados]),
        "posicao_media_fonte": round(statistics.mean(posicoes), 2) if posicoes else None,
        "por_origem": {o: sum(1 for r in resultados if r.origem == o) for o in sorted({r.origem for r in resultados})},
        "segundos_mediana": round(statistics.median(tempos), 2) if tempos else 0,
        "segundos_max": max(tempos, default=0),
    }


def relatorio_markdown(nome: str, configuracao: dict, resumo: dict, resultados: list[Resultado]) -> str:
    def pct(t):
        return "—" if t["taxa"] is None else f"{t['taxa']:.0%} ({t['acertos']}/{t['total']})"

    linhas = [
        f"# Avaliação das respostas — {nome}",
        "",
        "| Configuração | Valor |",
        "|---|---|",
        *(f"| {k} | {v} |" for k, v in configuracao.items()),
        "",
        "| Indicador | Resultado |",
        "|---|---|",
        f"| Casos aprovados | {pct(resumo['aprovados'])} |",
        f"| Fonte esperada citada | {pct(resumo['fonte'])} |",
        f"| Fonte esperada em 1º lugar | {pct(resumo['fonte_em_primeiro'])} |",
        f"| Conteúdo esperado na resposta | {pct(resumo['conteudo'])} |",
        f"| Conteúdo esperado nos trechos encontrados | {pct(resumo['evidencia'])} |",
        f"| Recusa correta (fora do acervo) | {pct(resumo['recusa'])} |",
        f"| Origem esperada | {pct(resumo['origem'])} |",
        f"| Origem das respostas | {', '.join(f'{k}: {v}' for k, v in resumo['por_origem'].items())} |",
        f"| Tempo (mediana / pior) | {resumo['segundos_mediana']} s / {resumo['segundos_max']} s |",
        "",
        "## Casos",
        "",
        "| Caso | Tema | Origem | Fonte | Trechos | Resposta | Recusa | Observação |",
        "|---|---|---|---|---|---|---|---|",
    ]
    marca = {True: "ok", False: "**falhou**", None: "—"}
    for r in resultados:
        obs = []
        if r.faltaram:
            obs.append("faltou: " + ", ".join(r.faltaram))
        if r.proibidos:
            obs.append("não devia conter: " + ", ".join(r.proibidos))
        if r.fonte_ok is False:
            obs.append("citou: " + ("; ".join(r.fontes_citadas[:3]) or "nenhuma"))
        if r.origem_ok is False:
            obs.append(f"origem {r.origem}")
        fonte = marca[r.fonte_ok] + (f" ({r.posicao_fonte}º)" if r.posicao_fonte and r.posicao_fonte > 1 else "")
        linhas.append(
            f"| {r.id} | {r.tema} | {r.origem} | {fonte} | {marca[r.evidencia_ok]} | {marca[r.conteudo_ok]} | "
            f"{marca[r.recusa_ok]} | "
            f"{'; '.join(obs).replace('|', '/')} |"
        )
    return "\n".join(linhas) + "\n"


def como_json(nome: str, configuracao: dict, resumo: dict, resultados: list[Resultado]) -> str:
    return json.dumps(
        {"nome": nome, "configuracao": configuracao, "resumo": resumo, "casos": [asdict(r) for r in resultados]},
        ensure_ascii=False,
        indent=2,
        default=str,
    )
