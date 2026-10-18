from django.urls import path

from apps.conversas.consumers import ChatConsumer
from apps.notificacoes.consumers import EventosConsumer

websocket_urlpatterns = [
    path("ws/chat/", ChatConsumer.as_asgi()),
    path("ws/eventos/", EventosConsumer.as_asgi()),
]
