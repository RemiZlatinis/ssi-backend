from django.urls import path

from . import views

app_name = "dev_debug"

urlpatterns = [
    # Agent list dashboard
    path("", views.agent_list, name="agent_list"),
    # Agent detail dashboard
    path("agent/<uuid:agent_id>/", views.agent_detail, name="agent_detail"),
    # API endpoints for polling
    path("api/agents/", views.agent_list_api, name="agent_list_api"),
    path("api/agent/<uuid:agent_id>/", views.agent_api_detail, name="agent_api_detail"),
]
