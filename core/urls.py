from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AgentViewSet

router = DefaultRouter()
router.register(r"agents", AgentViewSet, basename="agent")


urlpatterns = [
    path("", include(router.urls)),
]
