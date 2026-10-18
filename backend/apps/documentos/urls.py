from rest_framework.routers import DefaultRouter

from .views import CategoriaViewSet, ColecaoViewSet, DocumentoViewSet

router = DefaultRouter()
router.register("documentos", DocumentoViewSet, basename="documento")
router.register("colecoes", ColecaoViewSet, basename="colecao")
router.register("categorias", CategoriaViewSet, basename="categoria")
urlpatterns = router.urls
