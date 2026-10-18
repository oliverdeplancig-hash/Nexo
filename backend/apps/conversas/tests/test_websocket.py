import pytest
from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser

from nexo.routing import websocket_urlpatterns

pytestmark = pytest.mark.django_db(transaction=True)


async def _conectar(usuario):
    comunicador = WebsocketCommunicator(URLRouter(websocket_urlpatterns), "/ws/chat/")
    comunicador.scope["user"] = usuario
    conectado, codigo = await comunicador.connect()
    return comunicador, conectado, codigo


def test_conexao_anonima_e_recusada():
    async def _teste():
        comunicador, conectado, codigo = await _conectar(AnonymousUser())
        assert not conectado and codigo == 4401
        await comunicador.disconnect()

    async_to_sync(_teste)()


def test_fluxo_de_pergunta_em_streaming(usuarios, criar_documento):
    criar_documento("Manual de diárias", "As diárias devem ser solicitadas com cinco dias de antecedência.")
    usuario = usuarios["gp"]

    async def _teste():
        comunicador, conectado, _ = await _conectar(usuario)
        assert conectado
        assert (await comunicador.receive_json_from())["tipo"] == "pronto"
        await comunicador.send_json_to({"tipo": "mensagem", "texto": "antecedência das diárias"})
        tipos = []
        while True:
            evento = await comunicador.receive_json_from(timeout=10)
            tipos.append(evento["tipo"])
            if evento["tipo"] in ("resposta", "erro"):
                break
        await comunicador.disconnect()
        return tipos, evento

    tipos, final = async_to_sync(_teste)()
    assert tipos[0] == "conversa"
    assert "token" in tipos
    assert final["tipo"] == "resposta"
    assert final["mensagem"]["fontes"]
