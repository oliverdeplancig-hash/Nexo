"""Fila de geração da IA local (ADR-020).

O LLM é o recurso mais caro do Nexo: num computador comum ele atende uma ou duas respostas por vez.
Com muitas pessoas usando ao mesmo tempo, as gerações esperam a vez numa fila curta e com prazo:

- no máximo NEXO_IA_CONCORRENCIA gerações simultâneas por processo do servidor web;
- no máximo NEXO_IA_FILA_MAXIMA perguntas esperando; acima disso, ou passado NEXO_IA_ESPERA_MAXIMA
  segundos, a pergunta é respondida na hora com os trechos encontrados (resposta extrativa, ADR-006),
  em vez de deixar a pessoa esperando sem fim.

Motor determinístico (ADR-003), busca e "sem fontes" não passam por aqui: não usam o LLM.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from weakref import WeakKeyDictionary

from django.conf import settings


class IAOcupada(Exception):
    """Fila cheia ou espera longa demais. O orquestrador responde com os trechos encontrados."""


_estados: WeakKeyDictionary = WeakKeyDictionary()  # um semáforo por laço de eventos


def _estado() -> dict:
    laco = asyncio.get_running_loop()
    limite = max(1, settings.NEXO_IA["CONCORRENCIA"])
    estado = _estados.get(laco)
    if estado is None or estado["limite"] != limite:
        estado = {"semaforo": asyncio.Semaphore(limite), "limite": limite, "esperando": 0, "gerando": 0}
        _estados[laco] = estado
    return estado


@asynccontextmanager
async def vaga(avisar_posicao: Callable[[int], Awaitable[None]] | None = None):
    estado = _estado()
    semaforo: asyncio.Semaphore = estado["semaforo"]
    if semaforo.locked():
        if estado["esperando"] >= settings.NEXO_IA["FILA_MAXIMA"]:
            raise IAOcupada()
        estado["esperando"] += 1
        try:
            if avisar_posicao:
                await avisar_posicao(estado["esperando"])
            await asyncio.wait_for(semaforo.acquire(), timeout=settings.NEXO_IA["ESPERA_MAXIMA_SEGUNDOS"])
        except TimeoutError:
            raise IAOcupada() from None
        finally:
            estado["esperando"] -= 1
    else:
        await semaforo.acquire()
    estado["gerando"] += 1
    try:
        yield
    finally:
        estado["gerando"] -= 1
        semaforo.release()
