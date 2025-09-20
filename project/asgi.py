"""
ASGI config for project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from servestatic import ServeStaticASGI

from .settings import STATIC_ROOT

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

django_asgi_app = get_asgi_application()

if os.environ.get("ENVIRONMENT") == "production":
    django_asgi_app = ServeStaticASGI(django_asgi_app, root=STATIC_ROOT)

import core.routing  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": URLRouter(core.routing.websocket_urlpatterns),
    }
)
