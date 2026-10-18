"""Normalização de texto em português, determinística e sem dependências.

Usada pelo motor determinístico e pelo diretório de setores. A mesma entrada
sempre produz a mesma saída: nada aqui depende de modelo estatístico.
"""

from __future__ import annotations

import re
import unicodedata

_STOPWORDS_BRUTAS = """
    a à ao aos as às até com como da das de del dela delas dele deles do dos e é
    em entre era essa esse esta este eu foi há isso isto já la lhe lo mais mas me
    meu minha muito na nas nem no nos nós o os ou para pela pelas pelo pelos por
    qual quais quando que quem se sem ser seu seus sua suas são só também te tem
    tenho ter um uma umas uns você vocês vos preciso gostaria saber pode podem
    posso favor sobre onde algum alguma minhas meus faço faco fazer faz quero
    sabe devo consigo consegue alguém alguem ola olá bom dia boa tarde noite obrigado
    """.split()

_PONTUACAO = re.compile(r"[^\w\s]", flags=re.UNICODE)
_ESPACOS = re.compile(r"\s+")

# Sufixos removidos em ordem (do mais longo para o mais curto). É um radicalizador
# propositalmente simples: estável, previsível e fácil de auditar.
_SUFIXOS = (
    ("ções", "cao"),
    ("coes", "cao"),
    ("ção", "cao"),
    ("sões", "sao"),
    ("soes", "sao"),
    ("mente", ""),
    ("ais", "al"),
    ("eis", "el"),
    ("óis", "ol"),
    ("ois", "ol"),
    ("ões", "ao"),
    ("oes", "ao"),
    ("ães", "ao"),
    ("aes", "ao"),
    ("res", "r"),
    ("es", "e"),
    ("s", ""),
)


def remover_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


# Comparadas sempre com texto já normalizado (sem acentos).
STOPWORDS = frozenset(remover_acentos(p) for p in _STOPWORDS_BRUTAS)


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos, sem pontuação e com espaços simples."""
    texto = remover_acentos((texto or "").lower())
    texto = _PONTUACAO.sub(" ", texto)
    return _ESPACOS.sub(" ", texto).strip()


# Terminações verbais e vogal final: removidas depois do plural, para que
# "solicito", "solicitar" e "solicitação" convirjam para o mesmo radical.
_TERMINACOES = ("ando", "endo", "indo", "ado", "ada", "ido", "ida", "ar", "er", "ir", "a", "e", "o")


def radical(palavra: str) -> str:
    if len(palavra) <= 3 or palavra.isdigit():
        return palavra
    for sufixo, troca in _SUFIXOS:
        sufixo_sem_acento = remover_acentos(sufixo)
        if palavra.endswith(sufixo_sem_acento) and len(palavra) - len(sufixo_sem_acento) >= 3:
            palavra = palavra[: -len(sufixo_sem_acento)] + troca
            break
    if palavra.endswith("cao") and len(palavra) > 6:
        palavra = palavra[:-3]
    for terminacao in _TERMINACOES:
        if palavra.endswith(terminacao) and len(palavra) - len(terminacao) >= 4:
            return palavra[: -len(terminacao)]
    return palavra


def tokens(texto: str) -> list[str]:
    """Radicais significativos, na ordem em que aparecem (com repetição removida)."""
    vistos: dict[str, None] = {}
    for palavra in normalizar(texto).split():
        if palavra in STOPWORDS:
            continue
        vistos.setdefault(radical(palavra), None)
    return list(vistos)


def dice(a: set[str] | list[str], b: set[str] | list[str]) -> float:
    """Coeficiente de Dice entre dois conjuntos de tokens (0 a 1)."""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return 2 * len(sa & sb) / (len(sa) + len(sb))


def cobertura(necessarios: set[str] | list[str], presentes: set[str] | list[str]) -> float:
    """Fração de `necessarios` que aparece em `presentes`."""
    sn = set(necessarios)
    if not sn:
        return 0.0
    return len(sn & set(presentes)) / len(sn)
