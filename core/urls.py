from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AgentMeView,
    AgentRegisterView,
    AgentRegistrationStatusView,
    AgentUnregisterView,
    AgentViewSet,
    CompleteAgentRegistrationView,
    InitiateAgentRegistrationView,
    sse_agent_status,
)

router = DefaultRouter()
router.register(r"agents", AgentViewSet, basename="agent")


urlpatterns = [
    path("agents/register/", AgentRegisterView.as_view(), name="agent-register"),
    path(
        "agents/register/initiate/",
        InitiateAgentRegistrationView.as_view(),
        name="agent-register-initiate",
    ),
    path(
        "agents/register/complete/",
        CompleteAgentRegistrationView.as_view(),
        name="agent-register-complete",
    ),
    path(
        "agents/register/status/<uuid:registration_id>/",
        AgentRegistrationStatusView.as_view(),
        name="agent-register-status",
    ),
    path("agents/unregister/", AgentUnregisterView.as_view(), name="agent-unregister"),
    path("agents/me/", AgentMeView.as_view(), name="agent-me"),
    path("sse/agents/", sse_agent_status, name="sse_agent_status"),
    path("", include(router.urls)),
]
