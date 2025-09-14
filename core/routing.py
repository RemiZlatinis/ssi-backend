from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/agent/<uuid:agent_key>/", consumers.AgentConsumer.as_asgi()),
]
