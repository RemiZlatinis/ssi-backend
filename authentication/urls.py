from django.urls import include, path

from . import views

urlpatterns = [
    # This automatically includes:
    # - api/app/v1/auth/...     (For Native/Expo)
    # - api/browser/v1/auth/... (For Web/Browser)
    path("", include("allauth.headless.urls")),
    # Required for the standard callback mechanism for the "Redirect Flow"
    # This enables: /accounts/google/login/callback/
    path("auth/", include("allauth.socialaccount.providers.google.urls")),
    # CSRF token endpoint for headless web clients
    # Required because Django is used without templates
    path("auth/csrf/", views.CsrfTokenView.as_view(), name="csrf-token"),
]
