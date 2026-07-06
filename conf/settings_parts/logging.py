import os

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "verbose_console": {
            "format": "[{asctime}] [{levelname}] \033[31;1;4m[{module}]\033[0m {message}",
            "style": "{",
        },
        "verbose_file": {
            "format": "[{asctime}] [{levelname}] [{module}] [{name}] [{process:d}] [{message}]",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose_console",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "verbose_file",
            "filename": "/logs/django.log" if os.path.exists("/logs/django.log") else "/dev/null",
            "maxBytes": 1024 * 1024 * 15,  # 15MB
            "backupCount": 10,
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        }
    },
    "root": {
        "handlers": [
            "console",
            "file",
        ],
        "formatter": "simple",
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": [
                "console",
                "file",
            ],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": [
                "console",
                "file",
            ],
            "level": "DEBUG",
            "filters": ["require_debug_true"],
            "propagate": False,
        },
    },
}
