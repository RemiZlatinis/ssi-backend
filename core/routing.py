from typing import Callable, cast

from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path(
        "ws/agent/<str:agent_key>/",
        # Cast the ASGI application to a generic Callable to satisfy django-stubs
        cast(Callable, consumers.AgentConsumer.as_asgi()),
    ),
]
