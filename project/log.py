import os
import sys
from pathlib import Path

import sentry_sdk

BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = True if ENVIRONMENT == "development" else False

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

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
            "level": LOG_LEVEL,
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
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "authentication": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "notifications": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

if ENVIRONMENT == "production":
    DSN = os.getenv("SENTRY_DSN")
    if DSN:
        sentry_sdk.init(
            dsn=DSN,
            traces_sample_rate=0.1,
            send_default_pii=True,
        )
    else:
        raise ValueError("SENTRY_DSN is not set for a production environment!")
