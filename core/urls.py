from django.urls import path

from .views import AgentMeView

urlpatterns = [
    path("agents/me/", AgentMeView.as_view(), name="agent-me"),
]
