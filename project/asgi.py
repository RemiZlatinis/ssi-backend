"""
ASGI config for project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import re_path
from servestatic import ServeStaticASGI

from .settings import DEBUG, STATIC_ROOT

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

django_asgi_app = get_asgi_application()

if os.environ.get("ENVIRONMENT") == "production":
    django_asgi_app = ServeStaticASGI(django_asgi_app, root=STATIC_ROOT)

import core.routing  # noqa: E402

# Build WebSocket patterns
websocket_patterns = core.routing.websocket_urlpatterns

# Add dev_debug WebSocket patterns and middleware only in DEBUG mode
if DEBUG:
    import dev_debug.routing  # noqa: E402
    from dev_debug.middleware import AgentMessageSnifferMiddleware  # noqa: E402

    websocket_patterns = [
        *websocket_patterns,
        *dev_debug.routing.websocket_urlpatterns,
    ]
    websocket_app = AgentMessageSnifferMiddleware(URLRouter(websocket_patterns))
else:
    websocket_app = URLRouter(websocket_patterns)

application = ProtocolTypeRouter(
    {
        "http": URLRouter(
            [
                *core.routing.http_urlpatterns,
                re_path(r"", django_asgi_app),
            ]
        ),
        "websocket": websocket_app,
    }
)
