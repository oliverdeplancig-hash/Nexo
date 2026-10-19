"""Fila de geração da IA (ADR-020)."""

import asyncio

import pytest
from django.test import override_settings

from apps.ia.fila import IAOcupada, vaga


def _cfg(**k):
    base = {"CONCORRENCIA": 1, "FILA_MAXIMA": 5, "ESPERA_MAXIMA_SEGUNDOS": 5.0}
    base.update(k)
    from django.conf import settings

    return override_settings(NEXO_IA={**settings.NEXO_IA, **base})


def test_limita_geracoes_simultaneas_e_avisa_posicao():
    async def _teste():
        gerando, maximo, posicoes = 0, 0, []

        async def gerar():
            nonlocal gerando, maximo

            async def aviso(n):
                posicoes.append(n)

            async with vaga(aviso):
                gerando += 1
                maximo = max(maximo, gerando)
                await asyncio.sleep(0.01)
                gerando -= 1

        await asyncio.gather(*(gerar() for _ in range(4)))
        return maximo, posicoes

    with _cfg(CONCORRENCIA=2):
        maximo, posicoes = asyncio.run(_teste())
    assert maximo == 2 and sorted(posicoes) == [1, 2]


def test_fila_cheia_responde_na_hora():
    async def _teste():
        async def ocupar():
            async with vaga():
                await asyncio.sleep(0.2)

        async def tentar():
            await asyncio.sleep(0.01)
            async with vaga():
                pass

        resultados = await asyncio.gather(ocupar(), tentar(), tentar(), return_exceptions=True)
        return [type(r).__name__ for r in resultados]

    with _cfg(FILA_MAXIMA=1):
        assert sorted(asyncio.run(_teste())) == ["IAOcupada", "NoneType", "NoneType"]


def test_espera_longa_desiste():
    async def _teste():
        async def ocupar():
            async with vaga():
                await asyncio.sleep(0.3)

        async def tentar():
            await asyncio.sleep(0.01)
            async with vaga():
                pass

        await asyncio.gather(ocupar(), tentar())

    with _cfg(ESPERA_MAXIMA_SEGUNDOS=0.05), pytest.raises(IAOcupada):
        asyncio.run(_teste())
