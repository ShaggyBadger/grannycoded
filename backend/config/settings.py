"""Settings shared by the local Django/Wagtail starter project."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = Path(os.environ.get("DJANGO_LOG_DIR", BASE_DIR / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)


def environment_bool(name: str, *, default: bool = False) -> bool:
    """Read a clearly spelled boolean value from the process environment."""
    value = os.environ.get(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(
        f"{name} must be a boolean value such as true or false; received {value!r}."
    )


def environment_list(name: str, *, default: str = "") -> list[str]:
    """Read a comma-separated environment setting as a clean list."""
    return [
        item.strip()
        for item in os.environ.get(name, default).split(",")
        if item.strip()
    ]


def required_environment(name: str) -> str:
    """Read a required environment value without including its value in errors."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be set for the selected storage backend.")
    return value


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is empty. Run ./scripts/init.sh to generate a local key."
    )

DEBUG = environment_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = environment_list(
    "DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1"
)
CSRF_TRUSTED_ORIGINS = environment_list("DJANGO_CSRF_TRUSTED_ORIGINS")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "home",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
]

USE_LINODE_OBJECT_STORAGE = environment_bool(
    "USE_LINODE_OBJECT_STORAGE", default=False
)
if USE_LINODE_OBJECT_STORAGE:
    INSTALLED_APPS.append("storages")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "wagtail.contrib.settings.context_processors.settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "website"),
        "USER": os.environ.get("POSTGRES_USER", "website"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("DATABASE_HOST", "db"),
        "PORT": os.environ.get("DATABASE_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Linode Object Storage exposes an S3-compatible API; this points the backend at
# the configured Linode endpoint and does not use AWS-hosted storage.
if USE_LINODE_OBJECT_STORAGE:
    LINODE_STORAGE_LOCATION = required_environment("LINODE_STORAGE_LOCATION").strip("/")
    if not LINODE_STORAGE_LOCATION:
        raise ImproperlyConfigured("LINODE_STORAGE_LOCATION must name a non-root prefix.")

    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": required_environment("LINODE_ACCESS_KEY_ID"),
            "secret_key": required_environment("LINODE_SECRET_ACCESS_KEY"),
            "bucket_name": required_environment("LINODE_STORAGE_BUCKET_NAME"),
            "endpoint_url": required_environment("LINODE_STORAGE_ENDPOINT"),
            "region_name": required_environment("LINODE_STORAGE_REGION"),
            "location": LINODE_STORAGE_LOCATION,
            "default_acl": os.environ.get("LINODE_STORAGE_DEFAULT_ACL", "public-read"),
            "querystring_auth": False,
            "file_overwrite": False,
        },
    }

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
LOG_FILE_HANDLERS = {
    f"{level.lower()}_file": {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": str(LOG_DIR / f"{level.lower()}.log"),
        "level": level,
        "maxBytes": 25 * 1024 * 1024,
        "backupCount": 1 if level == "CRITICAL" else 5,
        "encoding": "utf-8",
        "formatter": "file",
    }
    for level in LOG_LEVELS
}
LOG_HANDLERS = [*LOG_FILE_HANDLERS, "console"]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "file": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
        "console": {"format": "{levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        **LOG_FILE_HANDLERS,
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "console",
        },
    },
    "loggers": {
        "django": {"handlers": LOG_HANDLERS, "level": "INFO", "propagate": False},
        "django.request": {
            "handlers": LOG_HANDLERS,
            "level": "WARNING",
            "propagate": False,
        },
        "django.server": {
            "handlers": LOG_HANDLERS,
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {"handlers": LOG_HANDLERS, "level": "DEBUG"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
WAGTAIL_SITE_NAME = os.environ.get("WAGTAIL_SITE_NAME", "New Website")
WAGTAILADMIN_BASE_URL = os.environ.get(
    "WAGTAILADMIN_BASE_URL", "http://localhost:8000"
)
