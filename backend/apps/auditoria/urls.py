from rest_framework.routers import DefaultRouter

from .views import EventoViewSet

router = DefaultRouter()
router.register("auditoria/eventos", EventoViewSet, basename="evento-auditoria")
urlpatterns = router.urls
