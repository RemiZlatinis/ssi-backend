from django.urls import include, path

from .views import GoogleLogin

urlpatterns = [
    path("google/", GoogleLogin.as_view(), name="google_login"),
    path("", include("dj_rest_auth.urls")),
]
