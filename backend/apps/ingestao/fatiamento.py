"""Divisão determinística de blocos em trechos para indexação e citação.

Um trecho nunca atravessa a fronteira de página, para que a citação
"p. N" seja sempre exata.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from apps.comum import texto as txt

from .extratores import Bloco


@dataclass
class TrechoGerado:
    ordem: int
    pagina: int | None
    secao: str
    texto: str


def _paragrafos(conteudo: str) -> list[str]:
    conteudo = re.sub(r"[ \t]+", " ", conteudo)
    partes = re.split(r"\n\s*\n|\n(?=\s*(?:Art\.|§|[IVX]+\s*[-–]|\d+\.\s))", conteudo)
    return [p.strip() for p in partes if p and p.strip()]


def fatiar(blocos: list[Bloco], tamanho: int = 1200, sobreposicao: int = 200) -> list[TrechoGerado]:
    trechos: list[TrechoGerado] = []

    def _emitir(pagina, secao, conteudo):
        conteudo = conteudo.strip()
        if len(conteudo) >= 20:
            trechos.append(TrechoGerado(len(trechos), pagina, secao, conteudo))

    for bloco in blocos:
        buffer = ""
        for paragrafo in _paragrafos(bloco.texto):
            while len(paragrafo) > tamanho:  # parágrafo gigante: corta em limite de frase
                corte = paragrafo.rfind(". ", 0, tamanho)
                corte = corte + 1 if corte > tamanho // 2 else tamanho
                if buffer:
                    _emitir(bloco.pagina, bloco.secao, buffer)
                    buffer = ""
                _emitir(bloco.pagina, bloco.secao, paragrafo[:corte])
                avanco = corte - sobreposicao if corte > 2 * sobreposicao else corte  # sempre avança
                paragrafo = paragrafo[avanco:]
            if len(buffer) + len(paragrafo) + 1 > tamanho and buffer:
                _emitir(bloco.pagina, bloco.secao, buffer)
                buffer = buffer[-sobreposicao:] if sobreposicao else ""
                espaco = buffer.find(" ")
                buffer = buffer[espaco + 1 :] if espaco >= 0 else buffer
            buffer = f"{buffer}\n{paragrafo}" if buffer else paragrafo
        if buffer:
            _emitir(bloco.pagina, bloco.secao, buffer)
    return trechos


_REFERENCIA = re.compile(
    r"\b(Portaria|Resolu[cç][aã]o|Instru[cç][aã]o Normativa|Decreto|Lei|Nota T[eé]cnica|Of[ií]cio|Despacho|Parecer)"
    r"\s*(n[ºo°.]*\s*)?(\d[\d./-]*\d)",
    flags=re.IGNORECASE,
)


def sugerir_referencia(conteudo: str) -> str:
    m = _REFERENCIA.search(conteudo[:4000])
    return m.group(0).strip()[:120] if m else ""


def sugerir_palavras_chave(conteudo: str, quantidade: int = 8) -> list[str]:
    """Termos mais frequentes (sem stopwords), desempate alfabético — determinístico."""
    palavras = [
        p for p in txt.normalizar(conteudo).split() if len(p) > 4 and p not in txt.STOPWORDS and not p.isdigit()
    ]
    contagem = Counter(palavras)
    return [p for p, _ in sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))[:quantidade]]
