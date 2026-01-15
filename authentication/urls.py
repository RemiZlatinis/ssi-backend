from django.urls import include, path

urlpatterns = [
    # This automatically includes:
    # - api/app/v1/auth/...     (For Native/Expo)
    # - api/browser/v1/auth/... (For Web/Browser)
    path("", include("allauth.headless.urls")),
]
