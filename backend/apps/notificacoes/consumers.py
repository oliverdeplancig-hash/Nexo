from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .servico import grupo_usuario


class EventosConsumer(AsyncJsonWebsocketConsumer):
    """Canal de eventos do usuário: notificações e progresso de processamento.

    O usuário só entra no próprio grupo; não há inscrição em canais arbitrários.
    """

    async def connect(self):
        usuario = self.scope.get("user")
        if not usuario or not usuario.is_authenticated or not usuario.is_active:
            await self.close(code=4401)
            return
        self.grupo = grupo_usuario(usuario.id)
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "grupo"):
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def receive_json(self, conteudo, **kwargs):
        if conteudo.get("tipo") == "ping":
            await self.send_json({"tipo": "pong"})

    async def evento_usuario(self, mensagem):
        await self.send_json(mensagem["evento"])
