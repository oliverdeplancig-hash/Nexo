from rest_framework.routers import DefaultRouter

from .views import SetorViewSet

router = DefaultRouter()
router.register("setores", SetorViewSet, basename="setor")
urlpatterns = router.urls
