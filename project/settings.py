"""Django settings for Service Status Indicator (SSI)"""

import os
import sys
from pathlib import Path
from typing import Any, cast

import dj_database_url
import sentry_sdk
from django.utils.csp import CSP
from dotenv import load_dotenv

################################################################################
#                             ENVIRONMENT VARIABLES                            #
################################################################################

# Load environment variables in Cascading Order (Highest to Lowest precedence):
# 1. System Environment Variables (Highest priority, never overwritten)
# 2. .env (Local configuration - only loaded if variable is missing from System)
# 3. .env.development (Shared defaults - only loaded if variable is missing
#     from both above and the environment is not explicitly set to production)

load_dotenv(override=False)  # Loads .env (Does not override existing variables)

# Shared defaults is loaded if the environment is not explicitly set to production
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv(
        Path(__file__).resolve().parent.parent / ".env.development", override=False
    )


################################################################################
#                                  SETTINGS                                    #
################################################################################

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment is controlled by environment variable, defaults to development
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# DEBUG is controlled by environment variable
# defaults to False on production and True on development environment
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# SECRET_KEY is mandatory from environment variables
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set!")

# Allowed hosts defaults to only 127.0.0.1
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "127.0.0.1").split(",")]

# CSRF trusted origins - typically required for production HTTPS
CSRF_TRUSTED_ORIGINS = []
if host_env := os.getenv("HOST"):
    CSRF_TRUSTED_ORIGINS = [f"https://{h.strip()}" for h in host_env.split(",")]

# CORS allowed origins
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]


INSTALLED_APPS = [
    # Priority apps
    "daphne",  # This "hijack" the runserver command from Django during development
    #
    #
    # Default Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    #
    #
    # Third party
    "rest_framework",
    "channels",
    "allauth",
    "allauth.headless",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "corsheaders",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.contrib.migrations",
    "dbbackup",
    #
    #
    # Project
    "core",
    "notifications",
    "authentication",
    "dbbackup_admin",
]

# Development-only apps
if DEBUG:
    INSTALLED_APPS.append("dev_debug")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
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

# Content Security Policy settings (report-only mode)
SECURE_CSP_REPORT_ONLY = {
    "default-src": [CSP.SELF],
    "script-src": [
        CSP.SELF,
        "'unsafe-inline'",  # Required for Django Admin
    ],
    "style-src": [
        CSP.SELF,
        "'unsafe-inline'",  # Required for Django Admin
    ],
    "img-src": [CSP.SELF, "data:", "https:", "*"],
    "font-src": [CSP.SELF, "https:"],
    "connect-src": [CSP.SELF],
    "media-src": [CSP.SELF],
    "object-src": [CSP.NONE],
    "frame-src": [CSP.NONE],
    "frame-ancestors": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
}

# Database configuration using DATABASE_URL (fallbacks to components)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": {
            **cast(dict[str, Any], dj_database_url.parse(DATABASE_URL)),
            "CONN_MAX_AGE": (
                # Setting it to 0 close DB connections immediately after the query.
                # This is a "requirement" for ASGI (Daphne) to prevent long-lived
                # streams (SSE/WebSockets) from exhausting the database connection
                # pool while idling.
                0
            ),
        }
    }
    # Production-specific safety and performance options
    if ENVIRONMENT == "production":
        DATABASES["default"].setdefault("OPTIONS", {})
        DATABASES["default"]["OPTIONS"].update(
            {
                "sslmode": "require",
                "connect_timeout": 10,
            }
        )
else:
    # Safety check for production
    if ENVIRONMENT == "production":
        raise ValueError("DATABASE_URL is not set for a production environment!")

    # Fallback to individual components (mainly for local development)
    DATABASES = {
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

STATICFILES_DIRS = [
    BASE_DIR / "assets",
]

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
                "django.template.context_processors.csp",
            ],
        },
    },
]

STORAGES = {
    "staticfiles": {
        "BACKEND": "servestatic.storage.CompressedManifestStaticFilesStorage",
    },
    "dbbackup": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": BASE_DIR / "backups",
        },
    },
}

TASKS = {
    "default": {
        "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
    },
}

SITE_ID = 1  # The one and only site on DB. This is required for the django-allauth

# django-allauth settings
ACCOUNT_LOGINS = {"email", "username"}  # Allow login with either email or username
ACCOUNT_EMAIL_VERIFICATION = "none"  # Allow active user without verified email
SOCIALACCOUNT_AUTO_SIGNUP = (
    True  # Automatically sign up users on successful social login
)
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True  # Auto-link social accounts with emails

# Headless configuration (API-only mode for Expo SDK clients - mobile and web)
HEADLESS_ONLY = True
HEADLESS_CLIENTS = ["app", "browser"]  # We support both mobile and browser auth flows
HEADLESS_ADAPTER = "authentication.adapters.CustomHeadlessAdapter"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # X-Session-Tokens for mobile
        "allauth.headless.contrib.rest_framework.authentication.XSessionTokenAuthentication",
        # SessionAuthentication for web clients (cookie-based)
        "rest_framework.authentication.SessionAuthentication",
    ),
}

# django_channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://valkey:6379/0")],
        },
    },
}

# dbbackup settings
aws_s3_settings = {
    "AWS_S3_ACCESS_KEY_ID": os.getenv("AWS_S3_ACCESS_KEY_ID"),
    "AWS_S3_SECRET_ACCESS_KEY": os.getenv("AWS_S3_SECRET_ACCESS_KEY"),
    "AWS_S3_REGION_NAME": os.getenv("AWS_S3_REGION_NAME"),
    "AWS_S3_ENDPOINT_URL": os.getenv("AWS_S3_ENDPOINT_URL"),
    "AWS_STORAGE_BUCKET_NAME": os.getenv("AWS_STORAGE_BUCKET_NAME"),
}
# We assume intention to use S3 backups if any of the AWS_S3 variables are set
# but we raise ValueError to prevent a "partial setup".
if any(aws_s3_settings.values()):
    if not all(aws_s3_settings.values()):
        raise ValueError(
            "All AWS S3 environment variables (AWS_S3_ACCESS_KEY_ID, "
            "AWS_S3_SECRET_ACCESS_KEY, AWS_S3_REGION_NAME, "
            "AWS_S3_ENDPOINT_URL, AWS_STORAGE_BUCKET_NAME) must be set for S3 backups."
        )
    # Then, we set the S3 storage backend for dbbackup
    STORAGES["dbbackup"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "access_key": aws_s3_settings["AWS_S3_ACCESS_KEY_ID"],
            "secret_key": aws_s3_settings["AWS_S3_SECRET_ACCESS_KEY"],
            "bucket_name": aws_s3_settings["AWS_STORAGE_BUCKET_NAME"],
            "region_name": aws_s3_settings["AWS_S3_REGION_NAME"],
            "endpoint_url": aws_s3_settings["AWS_S3_ENDPOINT_URL"],
        },
    }


################################################################################
#                                  LOGGING                                     #
################################################################################

# The log level can be controlled from the environment variable LOG_LEVEL
# defaults to DEBUG if DEBUG is True, otherwise INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO").upper()

# Handler levels (Set these to the lowest you ever want to see)
# We set console to DEBUG so that per-app overrides actually work
CONSOLE_LEVEL = "DEBUG" if DEBUG else LOG_LEVEL

# Ensure the logs directory exists for the RotatingFileHandlers
(BASE_DIR / "logs").mkdir(exist_ok=True)

# Logging configurations
# There are 3 formatters (verbose, simple, json),
# 2 handlers (console, file),
# 2 package loggers (django, django.request),
# and 4 app loggers (core, authentication, notifications, dbbackup_admin).
# The LOG_LEVEL environment variable controls the log level for all loggers,
# but can be overridden for each app using a LOG_LEVEL_[APP_NAME].
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} ({filename}:{lineno}) {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "json": {
            "format": (
                '{{"time": "{asctime}", "level": "{levelname}", "logger": "{name}", '
                '"file": "{filename}:{lineno}", "message": "{message}"}}'
            ),
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": CONSOLE_LEVEL,
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "verbose" if DEBUG else "json",
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/django.log"),
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/errors.log"),
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 3,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": os.getenv("LOG_LEVEL_DJANGO", "INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": os.getenv("LOG_LEVEL_DJANGO_REQUEST", "ERROR"),
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file"],
            "level": os.getenv("LOG_LEVEL_CORE", LOG_LEVEL).upper(),
            "propagate": False,
        },
        "authentication": {
            "handlers": ["console", "file"],
            "level": os.getenv("LOG_LEVEL_AUTHENTICATION", LOG_LEVEL).upper(),
            "propagate": False,
        },
        "notifications": {
            "handlers": ["console", "file"],
            "level": os.getenv("LOG_LEVEL_NOTIFICATIONS", LOG_LEVEL).upper(),
            "propagate": False,
        },
        "dbbackup_admin": {
            "handlers": ["console", "file"],
            "level": os.getenv("LOG_LEVEL_DBBACKUP_ADMIN", LOG_LEVEL).upper(),
            "propagate": False,
        },
    },
}

# Initialize Sentry or raise an error if SENTRY_DSN is not set on production
if ENVIRONMENT == "production":
    DSN = os.getenv("SENTRY_DSN")
    if DSN:
        sentry_sdk.init(
            dsn=DSN,
            traces_sample_rate=0.1,
            send_default_pii=True,
        )
    else:
        # TODO: Maybe change this to a warning
        raise ValueError("SENTRY_DSN is required on production environment!")
