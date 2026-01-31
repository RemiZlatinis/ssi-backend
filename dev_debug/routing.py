from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path(
        "dev-debug/ws/agent/<str:agent_key>/",
        consumers.DebugDashboardConsumer.as_asgi(),
    ),
]
