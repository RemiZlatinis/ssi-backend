from django.urls import path

from .views import AgentMeView, AgentRegisterView, AgentUnregisterView

urlpatterns = [
    path("agents/register/", AgentRegisterView.as_view(), name="agent-register"),
    path("agents/unregister/", AgentUnregisterView.as_view(), name="agent-unregister"),
    path("agents/me/", AgentMeView.as_view(), name="agent-me"),
]
