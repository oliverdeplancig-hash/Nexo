from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CategoriaViewSet, ColecaoViewSet, DocumentoViewSet, painel_acervo

router = DefaultRouter()
router.register("documentos", DocumentoViewSet, basename="documento")
router.register("colecoes", ColecaoViewSet, basename="colecao")
router.register("categorias", CategoriaViewSet, basename="categoria")
urlpatterns = [path("painel/acervo/", painel_acervo, name="painel-acervo"), *router.urls]
