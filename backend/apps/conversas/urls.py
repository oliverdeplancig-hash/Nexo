from rest_framework.routers import DefaultRouter

from .views import ConversaViewSet

router = DefaultRouter()
router.register("conversas", ConversaViewSet, basename="conversa")
urlpatterns = router.urls
