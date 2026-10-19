"""Teste de carga do Nexo (ADR-020): simula muitas pessoas usando o sistema ao mesmo tempo.

Cada pessoa simulada abre o assistente (WebSocket), consulta duas telas (API) e faz uma pergunta a cada
--intervalo segundos, começando em momentos espalhados dentro do primeiro intervalo. Ao final mostra quantas
perguntas foram atendidas, o tempo até a resposta completa (mediana, 95% e pior caso), a origem das
respostas e quantas foram respondidas só com trechos porque a fila da IA estava cheia.

Use num ambiente de homologação ou fora do expediente: o teste gera conversas reais da conta usada.
Entra UMA vez com a conta informada e reaproveita a sessão para todas as pessoas simuladas (o limite de
tentativas de login por endereço continua valendo).

    python manage.py teste_carga --url https://nexo-pc --usuario servidor.demo --pessoas 100 --minutos 5
"""

from __future__ import annotations

import asyncio
import getpass
import json
import logging
import random
import ssl
import statistics
import time
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError

PERGUNTAS_PADRAO = [
    "Como solicito férias?",
    "Qual o prazo para pedir diárias?",
    "Como faço para solicitar acesso a um sistema?",
    "Quem é responsável pelo protocolo de documentos?",
    "Como pedir a manutenção de um equipamento?",
    "Quais documentos preciso para a licença capacitação?",
]


@dataclass
class Resultado:
    perguntas: int = 0
    respondidas: int = 0
    erros: Counter = field(default_factory=Counter)
    tempos: list[float] = field(default_factory=list)
    primeiro_retorno: list[float] = field(default_factory=list)
    origens: Counter = field(default_factory=Counter)
    tempos_por_origem: dict = field(default_factory=dict)
    ia_ocupada: int = 0
    na_fila: int = 0
    tempos_api: list[float] = field(default_factory=list)
    erros_api: int = 0


def _percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int(round(p / 100 * (len(ordenados) - 1))))]


class Command(BaseCommand):
    help = "Simula várias pessoas usando o Nexo ao mesmo tempo e mede os tempos de resposta (ADR-020)."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, help="Endereço do Nexo, ex.: https://nexo-pc")
        parser.add_argument("--usuario", required=True)
        parser.add_argument("--senha", help="Se omitida, é pedida no terminal.")
        parser.add_argument("--pessoas", type=int, default=100)
        parser.add_argument("--minutos", type=float, default=5)
        parser.add_argument("--intervalo", type=float, default=60, help="Segundos entre perguntas de cada pessoa.")
        parser.add_argument("--limite-resposta", type=float, default=300, help="Segundos até desistir de uma resposta.")
        parser.add_argument("--perguntas", help="Arquivo de texto com uma pergunta por linha.")
        parser.add_argument(
            "--sem-verificar-certificado",
            action="store_true",
            help="Aceita certificado autoassinado (só para o teste dentro da rede).",
        )

    def handle(self, *args, **opcoes):
        try:
            import httpx
            import websockets  # noqa: F401
        except ImportError as erro:
            raise CommandError(f"Dependência ausente para o teste de carga: {erro.name}.") from erro
        if opcoes["pessoas"] < 1 or opcoes["minutos"] <= 0 or opcoes["intervalo"] <= 0:
            raise CommandError("Pessoas, minutos e intervalo precisam ser positivos.")
        perguntas = PERGUNTAS_PADRAO
        if opcoes["perguntas"]:
            with open(opcoes["perguntas"], encoding="utf-8") as arq:
                perguntas = [linha.strip() for linha in arq if linha.strip()] or PERGUNTAS_PADRAO
        senha = opcoes["senha"] or getpass.getpass(f"Senha de {opcoes['usuario']}: ")
        self.verificar = not opcoes["sem_verificar_certificado"]
        self.base = opcoes["url"].rstrip("/")
        self._httpx = httpx
        logging.getLogger("httpx").setLevel(logging.WARNING)

        cookies = self._entrar(opcoes["usuario"], senha)
        self.stdout.write(
            f"Simulando {opcoes['pessoas']} pessoas por {opcoes['minutos']:g} min, "
            f"uma pergunta a cada {opcoes['intervalo']:g} s por pessoa…"
        )
        inicio = time.monotonic()
        resultado = asyncio.run(self._simular(cookies, perguntas, opcoes))
        self._relatorio(resultado, time.monotonic() - inicio, opcoes)

    # ------------------------------------------------------------------
    def _entrar(self, usuario: str, senha: str) -> dict:
        with self._httpx.Client(base_url=self.base, verify=self.verificar, timeout=30) as cliente:
            token = cliente.get("/api/v1/auth/csrf/").json()["csrfToken"]
            r = cliente.post(
                "/api/v1/auth/entrar/",
                json={"usuario": usuario, "senha": senha},
                headers={"X-CSRFToken": token, "Referer": self.base + "/"},
            )
            if r.status_code != 200:
                raise CommandError(f"Não foi possível entrar ({r.status_code}): {r.text[:200]}")
            if r.json().get("trocar_senha"):
                raise CommandError(
                    "A conta ainda está com senha temporária. Entre uma vez pelo navegador e crie a senha."
                )
            return dict(cliente.cookies)

    async def _simular(self, cookies: dict, perguntas: list[str], opcoes: dict) -> Resultado:
        resultado = Resultado()
        fim = time.monotonic() + opcoes["minutos"] * 60
        contexto_tls = None
        if self.base.startswith("https") and not self.verificar:
            contexto_tls = ssl.create_default_context()
            contexto_tls.check_hostname = False
            contexto_tls.verify_mode = ssl.CERT_NONE
        async with self._httpx.AsyncClient(
            base_url=self.base,
            verify=self.verificar,
            cookies=cookies,
            timeout=60,
            limits=self._httpx.Limits(max_connections=opcoes["pessoas"]),
        ) as api:
            await asyncio.gather(
                *(
                    self._pessoa(n, api, cookies, perguntas, opcoes, fim, contexto_tls, resultado)
                    for n in range(opcoes["pessoas"])
                )
            )
        return resultado

    async def _pessoa(self, n, api, cookies, perguntas, opcoes, fim, contexto_tls, resultado: Resultado):
        import websockets

        alvo = urlparse(self.base)
        ws_url = f"{'wss' if alvo.scheme == 'https' else 'ws'}://{alvo.netloc}/ws/chat/"
        cabecalhos = {"Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()), "Origin": self.base}
        await asyncio.sleep(random.uniform(0, opcoes["intervalo"]))  # espalha o começo das pessoas
        conversa_id = None
        try:
            async with websockets.connect(
                ws_url, additional_headers=cabecalhos, ssl=contexto_tls, open_timeout=30, max_size=2**22
            ) as ws:
                await asyncio.wait_for(ws.recv(), 30)  # "pronto"
                while time.monotonic() < fim:
                    ciclo = time.monotonic()
                    await self._telas(api, resultado)
                    conversa_id = await self._perguntar(ws, random.choice(perguntas), conversa_id, opcoes, resultado)
                    await asyncio.sleep(max(0.0, opcoes["intervalo"] - (time.monotonic() - ciclo)))
        except Exception as erro:  # conexão recusada, queda etc.: conta e segue com as outras pessoas
            resultado.erros[f"conexão: {erro.__class__.__name__}"] += 1

    async def _telas(self, api, resultado: Resultado):
        for caminho in ("/api/v1/auth/eu/", "/api/v1/documentos/?page_size=20"):
            t0 = time.monotonic()
            try:
                r = await api.get(caminho)
                if r.status_code != 200:
                    resultado.erros_api += 1
            except Exception:
                resultado.erros_api += 1
            resultado.tempos_api.append(time.monotonic() - t0)

    async def _perguntar(self, ws, pergunta, conversa_id, opcoes, resultado: Resultado):
        resultado.perguntas += 1
        t0 = time.monotonic()
        primeiro = None
        await ws.send(json.dumps({"tipo": "mensagem", "texto": pergunta, "conversa_id": conversa_id}))
        limite = t0 + opcoes["limite_resposta"]
        while True:
            restante = limite - time.monotonic()
            if restante <= 0:
                resultado.erros["sem resposta no prazo"] += 1
                await ws.send(json.dumps({"tipo": "interromper"}))
                return conversa_id
            evento = json.loads(await asyncio.wait_for(ws.recv(), restante))
            tipo = evento.get("tipo")
            if tipo == "conversa":
                conversa_id = evento["id"]
            elif tipo == "status" and evento.get("etapa") == "na_fila":
                resultado.na_fila += 1
            elif tipo == "token" and primeiro is None:
                primeiro = time.monotonic() - t0
            elif tipo == "aviso" and evento.get("codigo") == "ia_ocupada":
                resultado.ia_ocupada += 1
            elif tipo == "resposta":
                total = time.monotonic() - t0
                resultado.respondidas += 1
                resultado.tempos.append(total)
                resultado.primeiro_retorno.append(primeiro if primeiro is not None else total)
                origem = evento["mensagem"].get("origem", "?")
                resultado.origens[origem] += 1
                resultado.tempos_por_origem.setdefault(origem, []).append(total)
                return conversa_id
            elif tipo == "erro":
                resultado.erros[evento.get("codigo", "erro")] += 1
                return conversa_id

    # ------------------------------------------------------------------
    def _relatorio(self, r: Resultado, duracao: float, opcoes: dict):
        def seg(v):
            return f"{v:.1f} s"

        linhas = [
            "",
            f"Duração: {duracao / 60:.1f} min · pessoas simuladas: {opcoes['pessoas']}",
            f"Perguntas feitas: {r.perguntas} · respondidas: {r.respondidas} "
            f"({r.respondidas / max(1, duracao / 60):.1f} por minuto)",
            f"Resposta completa: mediana {seg(statistics.median(r.tempos) if r.tempos else 0)} · "
            f"95% em até {seg(_percentil(r.tempos, 95))} · pior {seg(max(r.tempos, default=0))}",
            f"Primeiro retorno na tela: mediana {seg(statistics.median(r.primeiro_retorno) if r.primeiro_retorno else 0)}"
            f" · 95% em até {seg(_percentil(r.primeiro_retorno, 95))}",
            "Origem das respostas: " + (", ".join(f"{k} {v}" for k, v in r.origens.most_common()) or "nenhuma"),
            *(
                f"  {origem}: mediana {seg(statistics.median(t))} · 95% em até {seg(_percentil(t, 95))}"
                for origem, t in sorted(r.tempos_por_origem.items())
            ),
            f"Esperaram na fila da IA: {r.na_fila} · respondidas só com trechos por fila cheia: {r.ia_ocupada}",
            f"Telas (API): {len(r.tempos_api)} consultas · 95% em até {seg(_percentil(r.tempos_api, 95))}"
            f" · falhas {r.erros_api}",
            "Erros: " + (", ".join(f"{k} {v}" for k, v in r.erros.most_common()) or "nenhum"),
        ]
        self.stdout.write("\n".join(linhas))
        if r.erros or r.erros_api or r.ia_ocupada:
            self.stdout.write(
                self.style.WARNING(
                    "Há respostas com erro ou só com trechos: veja docs/architecture/capacidade.md para ajustar."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Todas as perguntas foram atendidas pela via normal."))
