"""WebSocket do assistente (Django Channels).

Protocolo (JSON):
  cliente → servidor
    {"tipo": "mensagem", "texto": "...", "conversa_id": 12?, "documento_id": 5?}
    {"tipo": "interromper"}
    {"tipo": "ping"}
  servidor → cliente
    {"tipo": "pronto"}                                   conexão autorizada
    {"tipo": "conversa", "id", "titulo"}                  conversa criada/confirmada
    {"tipo": "status", "etapa", "texto"}                  analisando | consultando_fontes | gerando
    {"tipo": "token", "texto"}                            pedaço da resposta (streaming)
    {"tipo": "aviso", "codigo", "texto"}                  ex.: ia_indisponivel
    {"tipo": "resposta", "conversa_id", "mensagem"}       mensagem final persistida
    {"tipo": "erro", "codigo", "texto"}
    {"tipo": "pong"}

Segurança: sessão autenticada exigida no connect; a cada mensagem a conversa
é revalidada como do próprio usuário e as permissões documentais são
reavaliadas pelo orquestrador. Nada é transmitido para grupos compartilhados.
"""

import asyncio
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .orquestrador import ErroConversa, executar

logger = logging.getLogger("nexo.chat")


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        usuario = self.scope.get("user")
        if not usuario or not usuario.is_authenticated or not usuario.is_active:
            await self.close(code=4401)
            return
        if getattr(usuario, "senha_temporaria", False):  # precisa criar a própria senha antes (ADR-018)
            await self.close(code=4403)
            return
        self.tarefa: asyncio.Task | None = None
        self._cancelar = False
        await self.accept()
        await self.send_json({"tipo": "pronto"})

    async def disconnect(self, code):
        if getattr(self, "tarefa", None) and not self.tarefa.done():
            self._cancelar = True

    async def receive_json(self, conteudo, **kwargs):
        tipo = conteudo.get("tipo")
        if tipo == "ping":
            await self.send_json({"tipo": "pong"})
        elif tipo == "interromper":
            self._cancelar = True
        elif tipo == "mensagem":
            if self.tarefa and not self.tarefa.done():
                await self.send_json(
                    {"tipo": "erro", "codigo": "ocupado", "texto": "Aguarde a resposta atual ou interrompa-a."}
                )
                return
            usuario = await self._usuario_atual()
            if usuario is None:
                await self.close(code=4401)
                return
            self._cancelar = False
            self.tarefa = asyncio.create_task(self._processar(usuario, conteudo))
        else:
            await self.send_json({"tipo": "erro", "codigo": "tipo_invalido", "texto": "Mensagem não reconhecida."})

    @database_sync_to_async
    def _usuario_atual(self):
        """Recarrega o usuário: contas desativadas durante a sessão perdem acesso imediatamente."""
        from django.contrib.auth import get_user_model

        usuario = (
            get_user_model().objects.filter(pk=self.scope["user"].pk, is_active=True).select_related("setor").first()
        )
        return usuario

    async def _processar(self, usuario, conteudo):
        def _inteiro(valor):
            try:
                return int(valor) if valor not in (None, "") else None
            except (TypeError, ValueError):
                return None

        try:
            await executar(
                usuario,
                _inteiro(conteudo.get("conversa_id")),
                str(conteudo.get("texto") or ""),
                self.send_json,
                documento_id=_inteiro(conteudo.get("documento_id")),
                cancelado=lambda: self._cancelar,
            )
        except ErroConversa as erro:
            await self.send_json({"tipo": "erro", "codigo": erro.codigo, "texto": erro.mensagem})
        except Exception:
            logger.exception("Falha no processamento da mensagem")
            await self.send_json(
                {"tipo": "erro", "codigo": "falha_interna", "texto": "Falha temporária. Tente novamente."}
            )
