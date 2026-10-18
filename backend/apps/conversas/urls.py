from django.urls import path
from rest_framework.routers import DefaultRouter

from . import lacunas
from .views import ConversaViewSet

router = DefaultRouter()
router.register("conversas", ConversaViewSet, basename="conversa")
urlpatterns = [
    path("mensagens/<int:pk>/avaliacao/", lacunas.avaliar, name="mensagem-avaliacao"),
    path("avaliacoes/motivos/", lacunas.motivos, name="avaliacao-motivos"),
    path("lacunas/", lacunas.lacunas, name="lacunas"),
    path("lacunas/resumo/", lacunas.resumo, name="lacunas-resumo"),
    path("lacunas/<int:pk>/tratar/", lacunas.tratar, name="lacuna-tratar"),
    *router.urls,
]
