from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AgentMeView,
    AgentRegisterView,
    AgentUnregisterView,
    AgentViewSet,
    sse_agent_status,
)

router = DefaultRouter()
router.register(r"agents", AgentViewSet, basename="agent")


urlpatterns = [
    path("agents/register/", AgentRegisterView.as_view(), name="agent-register"),
    path("agents/unregister/", AgentUnregisterView.as_view(), name="agent-unregister"),
    path("agents/me/", AgentMeView.as_view(), name="agent-me"),
    path("sse/agent-status/", sse_agent_status, name="sse_agent_status"),
    path("", include(router.urls)),
]
