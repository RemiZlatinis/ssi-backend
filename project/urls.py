"""
Main URL configuration for the project.
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    # Redirect the root URL to the desired external site
    path(
        "",
        RedirectView.as_view(
            url="https://service-status-indicator.com", permanent=True
        ),
        name="root-redirect",
    ),
    # Admin site
    path("admin/", admin.site.urls),
    # API endpoints for core functionalities (agents, etc.)
    path("api/", include("core.urls")),
    # Authentication endpoints (login, logout, registration)
    path("api/", include("authentication.urls")),
    # Notification endpoints
    path("api/notifications/", include("notifications.urls")),
    # Health check
    path("api/health/", include("health_check.urls")),
]
