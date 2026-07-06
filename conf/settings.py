from datetime import timedelta
from pathlib import Path

from environs import Env

from .settings_parts.logging import LOGGING  # noqa: F401

env = Env()

BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY", default="django-insecure-^#eakb$v5$ic!uts@w-k=y=7imy-f(mt#*sl5up0**fa@34c+z")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "0.0.0.0", "heinapp-backend-service"])


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework.authtoken",
    "corsheaders",
    "djoser",
    "users",
    "core",
    "workshop",
    "contact",
    "calendar_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "conf.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "conf.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": f"django.db.backends.{env.str('DATABASE_ENGINE', 'postgresql')}",
        "NAME": env.str("DATABASE_NAME", default=None),
        "USER": env.str("DATABASE_USER", default=None),
        "PASSWORD": env.str("DATABASE_PASSWORD", default=None),
        "HOST": env.str("DATABASE_HOST", "localhost"),
        "PORT": env.str("DATABASE_PORT", default=None),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "de"

TIME_ZONE = "Europe/Berlin"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"

# Media files (User uploads)
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# JWT Authentication

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "EXCEPTION_HANDLER": "core.exception_handler.custom_exception_handler",
}


# Custom user model

AUTH_USER_MODEL = "users.User"


# Simple JWT settings

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_OBTAIN_SERIALIZER": "users.serializers.UserTokenObtainPairSerializer",
}

DJOSER = {
    "LOGIN_FIELD": "email",
    "USER_CREATE_PASSWORD_RETYPE": True,
    "TOKEN_MODEL": None,
    "SERIALIZERS": {
        "user_create_password_retype": "users.serializers.UserCreateSerializer",
        "user": "users.serializers.UserSerializer",
        "current_user": "users.serializers.UserSerializer",
        "token_create": "users.serializers.UserTokenObtainPairSerializer",
    },
    "PERMISSIONS": {
        "user": ["rest_framework.permissions.IsAuthenticated"],
        "user_list": ["rest_framework.permissions.IsAdminUser"],
    },
    "PASSWORD_RESET_CONFIRM_URL": "password-reset-confirm/{uid}/{token}",
    "USERNAME_RESET_CONFIRM_URL": "email-reset-confirm/{uid}/{token}",
    "ACTIVATION_URL": "activate/{uid}/{token}",
    "EMAIL_FRONTEND_DOMAIN": env.str("EMAIL_FRONTEND_DOMAIN", default="localhost:3000"),
    "EMAIL_FRONTEND_SITE_NAME": env.str("EMAIL_FRONTEND_SITE_NAME", default="HeiNa Baugemeinschaft"),
    "SEND_ACTIVATION_EMAIL": True,
    "SEND_CONFIRMATION_EMAIL": True,
    "EMAIL": {
        "activation": "users.email.ActivationEmail",
        "confirmation": "users.email.ConfirmationEmail",
        "password_reset": "users.email.PasswordResetEmail",
    },
}


# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# Test/Development: console (terminal output), locmem (in-memory), dummy (discard)
EMAIL_BACKEND = env.str("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env.str("EMAIL_HOST", default="")
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="backend@example.com")
ADMIN_EMAIL = env.str("ADMIN_EMAIL", default="admin@example.com")
BACKEND_BASE_URL = env.str("BACKEND_BASE_URL", default="http://localhost:8000")
FRONTEND_URL = env.str("EMAIL_FRONTEND_DOMAIN", default="http://localhost:3000")


# CORS settings

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])

CORS_ALLOW_HEADERS = [
    "common",
    "Content-Type",
    "Authorization",
]


# CSRF settings (important for reverse proxy)

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:3000"])


# Security settings for reverse proxy (Caddy)

# Trust X-Forwarded-Proto header from Caddy (for HTTPS detection)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Use secure cookies in production
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = False  # Caddy handles HTTP->HTTPS redirect


# CalDAV Configuration

CALDAV_CONFIG = {
    "url": env.str("CALDAV_URL", "https://your-caldav-server.com/caldav/"),
    "username": env.str("CALDAV_USER", "your-username"),
    "password": env.str("CALDAV_PASSWORD", "your-password"),
    "calendar_url": env.str("CALDAV_CALENDAR_URL", "default_calendar_url"),
}


BACKEND_BASE_URL = env.str("BACKEND_BASE_URL", default="http://localhost:8000")
