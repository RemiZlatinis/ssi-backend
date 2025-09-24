"""Django settings for Service Status Indicator (SSI) - Monitoring Framework project."""

import os
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

import dj_database_url
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

####################
# DEFAULT SETTINGS #
####################
DEBUG = False

ALLOWED_HOSTS = ["127.0.0.1"]
host_env = os.getenv("HOST")
if host_env:
    ALLOWED_HOSTS.append(host_env)

CORS_ALLOWED_ORIGINS = []
CORS_ALLOWED_ORIGINS_ENV = os.getenv("CORS_ALLOWED_ORIGINS")
if CORS_ALLOWED_ORIGINS_ENV:
    CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS_ENV.split(",")

INSTALLED_APPS = [
    # Priority apps
    "daphne",
    # Default Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework.authtoken",
    "channels",
    "allauth.headless",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "dj_rest_auth",
    "corsheaders",
    # Project
    "core",
    "notifications",
    "authentication",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "servestatic.middleware.ServeStaticMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

WSGI_APPLICATION = "project.wsgi.application"
ASGI_APPLICATION = "project.asgi.application"

DATABASES: dict[str, dict[str, Any]] = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("SQL_DATABASE"),
        "USER": os.getenv("SQL_USER"),
        "PASSWORD": os.getenv("SQL_PASSWORD"),
        "HOST": os.getenv("SQL_HOST"),
        "PORT": os.getenv("SQL_PORT"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

STORAGES = {
    "staticfiles": {
        "BACKEND": "servestatic.storage.CompressedManifestStaticFilesStorage",
    },
}

SITE_ID = 1  # The one and only site on DB. This is required for the django-allauth

# django-allauth settings
ACCOUNT_AUTHENTICATION_METHODS = {
    "username",  # Use the username, default on allauth is the email
}
ACCOUNT_EMAIL_VERIFICATION = "none"  # Allow active user without verified email
HEADLESS_ONLY = True  # Operate in headless mode
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True  # auto-link social accounts with emails.

# DRF settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

# dj-rest-auth settings
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_REFRESH_COOKIE": None,
    "USER_DETAILS_SERIALIZER": "authentication.serializers.CustomUserDetailsSerializer",
}

# rest_framework_simplejwt settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=365),  # TODO: Implement refresh mechanism
    "REFRESH_TOKEN_LIFETIME": timedelta(days=365),
}

# django_channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("valkey", 6379)],
        },
    },
}


###############################################
# SETTINGS OVERRIDES based on the environment #
###############################################
if ENVIRONMENT == "development":
    SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-default-for-development")
    DEBUG = True
    CORS_ALLOWED_ORIGINS += [
        "http://localhost:8081",  # Allow Expo's Web from local 8081 port
        "http://127.0.0.1:8081",
    ]

elif ENVIRONMENT == "production":
    _SECRET_KEY = os.getenv("SECRET_KEY")
    if not _SECRET_KEY:
        raise ValueError("SECRET_KEY is not set for a production environment!")
    SECRET_KEY = _SECRET_KEY

    host = os.getenv("HOST")
    if host:
        CSRF_TRUSTED_ORIGINS = [f"https://{host}"]

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set for a production environment!")
    else:
        DATABASES = {
            "default": cast(dict[str, Any], dj_database_url.parse(DATABASE_URL))
        }

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [os.environ.get("REDIS_URL")]},
        },
    }
else:
    raise ValueError(f"Invalid ENVIRONMENT value: {ENVIRONMENT}")
