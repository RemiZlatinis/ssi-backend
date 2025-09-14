from django.urls import path

from . import views
from .views import AgentMeView, AgentRegisterView, AgentUnregisterView

urlpatterns = [
    path("agents/register/", AgentRegisterView.as_view(), name="agent-register"),
    path("agents/unregister/", AgentUnregisterView.as_view(), name="agent-unregister"),
    path("agents/me/", AgentMeView.as_view(), name="agent-me"),
    path("sse/agent-status/", views.sse_agent_status, name="sse_agent_status"),
]
