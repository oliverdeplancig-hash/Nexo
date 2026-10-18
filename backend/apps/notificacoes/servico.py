import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notificacao

logger = logging.getLogger("nexo.notificacoes")


def grupo_usuario(usuario_id: int) -> str:
    return f"usuario_{usuario_id}"


def enviar_evento(usuario_id: int, evento: dict) -> None:
    """Envia um evento em tempo real somente ao grupo do próprio usuário."""
    camada = get_channel_layer()
    if camada is None:
        return
    try:
        async_to_sync(camada.group_send)(grupo_usuario(usuario_id), {"type": "evento.usuario", "evento": evento})
    except Exception:  # a notificação persistida continua disponível via REST
        logger.exception("Falha ao enviar evento em tempo real")


def notificar(
    usuario, tipo: str, titulo: str, texto: str = "", link: str = "", dados: dict | None = None
) -> Notificacao:
    notificacao = Notificacao.objects.create(
        usuario=usuario, tipo=tipo, titulo=titulo[:200], texto=texto[:500], link=link, dados=dados or {}
    )
    enviar_evento(
        usuario.id,
        {
            "tipo": "notificacao",
            "notificacao": {
                "id": notificacao.id,
                "tipo": tipo,
                "titulo": notificacao.titulo,
                "texto": notificacao.texto,
                "link": link,
                "criada_em": notificacao.criada_em.isoformat(),
            },
        },
    )
    return notificacao
