"""Roteamento determinístico: "qual setor pode me ajudar?"."""

from __future__ import annotations

from dataclasses import dataclass

from apps.comum import texto

from .models import Setor


@dataclass(frozen=True)
class SugestaoSetor:
    setor: Setor
    pontuacao: float
    termos: tuple[str, ...]


def _vocabulario(setor: Setor) -> set[str]:
    partes = [
        setor.nome,
        setor.sigla,
        setor.descricao,
        setor.competencias,
        " ".join(setor.tipos_demanda or []),
        " ".join(setor.servicos or []),
        " ".join(setor.procedimentos_relacionados or []),
        " ".join(setor.palavras_chave or []),
    ]
    return set(texto.tokens(" ".join(partes)))


def sugerir_setores(pergunta: str, limite: int = 3, minimo: float = 0.15) -> list[SugestaoSetor]:
    """Ordena setores pela fração dos termos da pergunta que eles cobrem.

    Desempate: maior número de termos em comum e, depois, sigla em ordem alfabética,
    garantindo que a mesma pergunta produza sempre a mesma lista.
    """
    termos = texto.tokens(pergunta)
    if not termos:
        return []
    resultado: list[SugestaoSetor] = []
    for setor in Setor.objects.filter(ativo=True):
        comuns = [t for t in termos if t in _vocabulario(setor)]
        if not comuns:
            continue
        pontuacao = round(len(comuns) / len(termos), 4)
        if pontuacao >= minimo:
            resultado.append(SugestaoSetor(setor, pontuacao, tuple(comuns)))
    resultado.sort(key=lambda s: (-s.pontuacao, -len(s.termos), s.setor.sigla))
    return resultado[:limite]
