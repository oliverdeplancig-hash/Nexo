from rest_framework.routers import DefaultRouter

from .views import RegraViewSet

router = DefaultRouter()
router.register("motor/regras", RegraViewSet, basename="regra")
urlpatterns = router.urls
