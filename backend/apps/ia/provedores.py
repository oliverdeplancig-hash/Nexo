"""Provedores de LLM e embeddings.

Produção: Ollama na própria máquina ou no servidor da instituição (nenhum dado
sai da rede). Testes e demonstração: provedor "falso", determinístico.
Novos provedores exigem ADR (ver docs/adr/ADR-004).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import re
import time
from collections.abc import AsyncIterator
from functools import lru_cache

import httpx
from django.conf import settings

from apps.comum import texto

logger = logging.getLogger("nexo.ia")


class ProvedorIndisponivel(Exception):
    """O serviço de IA não respondeu. O orquestrador degrada para resposta extrativa."""


class Provedor:
    nome = "base"

    def disponivel(self) -> bool:
        raise NotImplementedError

    def embed(self, textos: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def gerar_stream(self, mensagens: list[dict]) -> AsyncIterator[str]:
        raise NotImplementedError
        yield ""  # pragma: no cover


class ProvedorOllama(Provedor):
    nome = "ollama"

    def __init__(self):
        cfg = settings.NEXO_IA
        self.url = cfg["OLLAMA_URL"].rstrip("/")
        self.modelo_chat = cfg["MODELO_CHAT"]
        self.modelo_embedding = cfg["MODELO_EMBEDDING"]
        self.temperatura = cfg["TEMPERATURA"]
        self.timeout = cfg["TIMEOUT_SEGUNDOS"]
        self._ultima_verificacao = 0.0
        self._ultimo_estado = False

    def disponivel(self) -> bool:
        agora = time.monotonic()
        if agora - self._ultima_verificacao < 30:
            return self._ultimo_estado
        try:
            resposta = httpx.get(f"{self.url}/api/tags", timeout=2.0)
            self._ultimo_estado = resposta.status_code == 200
        except httpx.HTTPError:
            self._ultimo_estado = False
        self._ultima_verificacao = agora
        return self._ultimo_estado

    def embed(self, textos: list[str]) -> list[list[float]]:
        try:
            resposta = httpx.post(
                f"{self.url}/api/embed",
                json={"model": self.modelo_embedding, "input": textos},
                timeout=self.timeout,
            )
            resposta.raise_for_status()
        except httpx.HTTPError as erro:
            raise ProvedorIndisponivel(str(erro)) from erro
        vetores = resposta.json().get("embeddings") or []
        if len(vetores) != len(textos):
            raise ProvedorIndisponivel("Resposta de embeddings incompleta.")
        return vetores

    async def gerar_stream(self, mensagens: list[dict]) -> AsyncIterator[str]:
        corpo = {
            "model": self.modelo_chat,
            "messages": mensagens,
            "stream": True,
            "options": {"temperature": self.temperatura},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as cliente:
                async with cliente.stream("POST", f"{self.url}/api/chat", json=corpo) as resposta:
                    resposta.raise_for_status()
                    async for linha in resposta.aiter_lines():
                        if not linha:
                            continue
                        dado = json.loads(linha)
                        pedaco = (dado.get("message") or {}).get("content") or ""
                        if pedaco:
                            yield pedaco
                        if dado.get("done"):
                            break
        except httpx.HTTPError as erro:
            raise ProvedorIndisponivel(str(erro)) from erro


class ProvedorFalso(Provedor):
    """Determinístico, sem rede. Embeddings por hashing de radicais e geração
    extrativa que só repete o contexto recebido, citando-o."""

    nome = "falso"

    def __init__(self):
        self.dimensao = settings.NEXO_IA["DIMENSAO_EMBEDDING"]

    def disponivel(self) -> bool:
        return True

    def _vetor(self, conteudo: str) -> list[float]:
        vetor = [0.0] * self.dimensao
        for termo in texto.tokens(conteudo):
            indice = int(hashlib.sha1(termo.encode()).hexdigest(), 16) % self.dimensao
            vetor[indice] += 1.0
        norma = math.sqrt(sum(v * v for v in vetor)) or 1.0
        return [v / norma for v in vetor]

    def embed(self, textos: list[str]) -> list[list[float]]:
        return [self._vetor(t) for t in textos]

    async def gerar_stream(self, mensagens: list[dict]) -> AsyncIterator[str]:
        contexto = mensagens[-1]["content"]
        blocos = re.findall(r"\[(\d+)\][^\n]*\n(.+?)(?=\n\[\d+\]|\n---|\Z)", contexto, flags=re.S)
        if not blocos:
            yield "Não encontrei essa informação nos documentos autorizados."
            return
        partes = ["Com base nos documentos autorizados:\n\n"]
        for numero, conteudo in blocos[:3]:
            linhas = [re.sub(r"^[#>\s*-]+", "", x).strip() for x in conteudo.strip().split("\n")]
            frase = " ".join(x for x in linhas if x)[:280]
            partes.append(f"- {frase} [{numero}]\n")
        atraso = settings.NEXO_IA.get("FALSO_ATRASO", 0.0)
        for parte in partes:
            for palavra in re.split(r"(\s+)", parte):
                if palavra:
                    if atraso and not palavra.isspace():
                        await asyncio.sleep(atraso)
                    yield palavra


@lru_cache(maxsize=1)
def _instanciar(nome: str) -> Provedor:
    if nome == "falso":
        return ProvedorFalso()
    if nome == "ollama":
        return ProvedorOllama()
    raise ValueError(f"Provedor de IA desconhecido: {nome}")


def obter_provedor() -> Provedor:
    return _instanciar(settings.NEXO_IA["PROVEDOR"])
