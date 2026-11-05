"""Settings shared by the local Django/Wagtail starter project."""

import logging
import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from oscar.defaults import *  # noqa: F403

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
PUBLIC_SITE_URL = os.environ.get("PUBLIC_SITE_URL", "http://localhost:8000").rstrip("/")
GOOGLE_SITE_VERIFICATION = os.environ.get("GOOGLE_SITE_VERIFICATION", "").strip()
CUSTOM_ORDER_NOTIFICATION_EMAIL = os.environ.get(
    "CUSTOM_ORDER_NOTIFICATION_EMAIL", ""
).strip()
ORDER_NOTIFICATION_EMAIL = (
    os.environ.get("ORDER_NOTIFICATION_EMAIL", "").strip()
    or CUSTOM_ORDER_NOTIFICATION_EMAIL
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "").strip()
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = environment_bool("EMAIL_USE_TLS", default=True)
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
).strip()
if os.environ.get("DEFAULT_FROM_EMAIL"):
    DEFAULT_FROM_EMAIL = os.environ["DEFAULT_FROM_EMAIL"].strip()

# Stripe payments. Checkout stays closed unless the configured key matches the
# requested mode, so a live key copied into a development .env cannot charge a
# real card by accident.
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "").strip()
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_LIVE_MODE = environment_bool("STRIPE_LIVE_MODE", default=False)
STRIPE_CURRENCY = os.environ.get("STRIPE_CURRENCY", "usd").strip().lower()
STRIPE_CHECKOUT_EXPIRY_MINUTES = int(
    os.environ.get("STRIPE_CHECKOUT_EXPIRY_MINUTES", "35")
)
# sk_live_ is a full secret key; rk_live_ is a restricted key. Both move money.
STRIPE_KEY_IS_LIVE = STRIPE_SECRET_KEY.startswith(("sk_live_", "rk_live_"))
STRIPE_MODE_MISMATCH = bool(STRIPE_SECRET_KEY) and (
    STRIPE_KEY_IS_LIVE != STRIPE_LIVE_MODE
)
# Fail closed: a mismatched key leaves checkout visibly closed instead of
# taking the whole site down or charging the wrong account.
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY) and not STRIPE_MODE_MISMATCH
if STRIPE_MODE_MISMATCH:
    logging.getLogger("home.checkout").error(
        "Stripe is disabled: STRIPE_SECRET_KEY is a %s key but STRIPE_LIVE_MODE "
        "is %s. Set both consistently; see instructions/stripe-checkout-plan.md.",
        "live" if STRIPE_KEY_IS_LIVE else "test",
        "on" if STRIPE_LIVE_MODE else "off",
    )

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "home",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.flatpages",
    "django.contrib.humanize",
    "oscar.config.Shop",
    "wagtail.contrib.settings",
    "oscar.apps.analytics.apps.AnalyticsConfig",
    "oscar.apps.checkout.apps.CheckoutConfig",
    "oscar.apps.address.apps.AddressConfig",
    "oscar.apps.shipping.apps.ShippingConfig",
    "oscar.apps.catalogue.apps.CatalogueConfig",
    "oscar.apps.catalogue.reviews.apps.CatalogueReviewsConfig",
    "oscar.apps.communication.apps.CommunicationConfig",
    "oscar.apps.partner.apps.PartnerConfig",
    "oscar.apps.basket.apps.BasketConfig",
    "oscar.apps.payment.apps.PaymentConfig",
    "oscar.apps.offer.apps.OfferConfig",
    "oscar.apps.order.apps.OrderConfig",
    "oscar.apps.customer.apps.CustomerConfig",
    "oscar.apps.search.apps.SearchConfig",
    "oscar.apps.voucher.apps.VoucherConfig",
    "oscar.apps.wishlists.apps.WishlistsConfig",
    "oscar.apps.dashboard.apps.DashboardConfig",
    "oscar.apps.dashboard.reports.apps.ReportsDashboardConfig",
    "oscar.apps.dashboard.users.apps.UsersDashboardConfig",
    "oscar.apps.dashboard.orders.apps.OrdersDashboardConfig",
    "oscar.apps.dashboard.catalogue.apps.CatalogueDashboardConfig",
    "oscar.apps.dashboard.offers.apps.OffersDashboardConfig",
    "oscar.apps.dashboard.partners.apps.PartnersDashboardConfig",
    "oscar.apps.dashboard.pages.apps.PagesDashboardConfig",
    "oscar.apps.dashboard.ranges.apps.RangesDashboardConfig",
    "oscar.apps.dashboard.reviews.apps.ReviewsDashboardConfig",
    "oscar.apps.dashboard.vouchers.apps.VouchersDashboardConfig",
    "oscar.apps.dashboard.communications.apps.CommunicationsDashboardConfig",
    "oscar.apps.dashboard.shipping.apps.ShippingDashboardConfig",
    "widget_tweaks",
    "haystack",
    "treebeard",
    "easy_thumbnails",
    "django_tables2",
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
    "django.contrib.postgres",
]

SITE_ID = 1
AUTHENTICATION_BACKENDS = (
    "oscar.apps.customer.auth_backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
)
OSCAR_SHOP_NAME = "GrannyCoded"
OSCAR_SHOP_TAGLINE = "Found textiles, made into something new."
OSCAR_DEFAULT_CURRENCY = "USD"
OSCAR_HOMEPAGE = "/"
OSCAR_ALLOW_ANON_CHECKOUT = True
OSCAR_THUMBNAILER = "oscar.core.thumbnails.EasyThumbnails"
OSCAR_IMAGE_FOLDER = "products/%Y/%m"


def staff_dashboard_access(user, url_name, url_args, url_kwargs):
    """Restrict GrannyCoded's custom shop tools to staff users."""
    return user.is_staff


OSCAR_DASHBOARD_NAVIGATION += [
    {
        "label": "GrannyCoded",
        "icon": "fas fa-store",
        "access_fn": staff_dashboard_access,
        "children": [
            {
                "label": "Custom orders",
                "url_name": "custom_order_queue",
                "access_fn": staff_dashboard_access,
            },
            {
                "label": "Record in-person sale",
                "url_name": "record_manual_sale",
                "access_fn": staff_dashboard_access,
            },
            {
                "label": "Manage image assets",
                "url_name": "admin:home_imageasset_changelist",
                "access_fn": staff_dashboard_access,
            },
            {
                "label": "Link product images",
                "url_name": "admin:home_productimageasset_changelist",
                "access_fn": staff_dashboard_access,
            },
        ],
    },
]
OSCAR_INITIAL_ORDER_STATUS = "Pending"
OSCAR_INITIAL_LINE_STATUS = "Pending"
OSCAR_ORDER_STATUS_PIPELINE = {
    "Pending": ("Being processed", "Cancelled"),
    "Being processed": ("Complete", "Cancelled"),
    "Complete": (),
    "Cancelled": (),
}
OSCAR_LINE_STATUS_PIPELINE = {
    "Pending": ("Being processed", "Cancelled"),
    "Being processed": ("Shipped", "Collected", "Complete", "Cancelled"),
    "Shipped": ("Returned", "Complete"),
    "Collected": ("Returned", "Complete"),
    "Complete": ("Returned",),
    "Returned": (),
    "Cancelled": (),
}
OSCAR_ORDER_STATUS_CASCADE = {
    "Being processed": "Being processed",
    "Complete": "Complete",
    "Cancelled": "Cancelled",
}
HAYSTACK_CONNECTIONS = {
    "default": {"ENGINE": "haystack.backends.simple_backend.SimpleEngine"}
}

TESTING = "test" in sys.argv
USE_LINODE_OBJECT_STORAGE = environment_bool(
    "USE_LINODE_OBJECT_STORAGE", default=False
) and not TESTING
if USE_LINODE_OBJECT_STORAGE:
    INSTALLED_APPS.append("storages")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "oscar.apps.basket.middleware.BasketMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
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
                "home.context_processors.editorial_navigation",
                "home.seo.seo_metadata",
                "oscar.apps.search.context_processors.search_form",
                "oscar.apps.checkout.context_processors.checkout",
                "oscar.apps.communication.notifications.context_processors.notifications",
                "oscar.core.context_processors.metadata",
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
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "home.storage.ULIDFileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "public_images": {
        "BACKEND": "home.storage.ULIDFileSystemStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT / "images" / "public",
            "base_url": f"{MEDIA_URL}images/public/",
        },
    },
    "private_images": {
        "BACKEND": "home.storage.ULIDFileSystemStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT / "images" / "private",
            "base_url": f"{MEDIA_URL}images/private/",
        },
    },
}

# Linode Object Storage exposes an S3-compatible API; this points the backend at
# the configured Linode endpoint. Static files remain on the local staticfiles
# backend; public and private image storages use separate object ACLs.
if USE_LINODE_OBJECT_STORAGE:
    LINODE_STORAGE_LOCATION = os.environ.get("LINODE_STORAGE_LOCATION", "images/public").strip("/")
    LINODE_PRIVATE_STORAGE_LOCATION = os.environ.get(
        "LINODE_PRIVATE_STORAGE_LOCATION", "images/private"
    ).strip("/")
    if not LINODE_STORAGE_LOCATION:
        raise ImproperlyConfigured("LINODE_STORAGE_LOCATION must name a non-root prefix.")
    if not LINODE_PRIVATE_STORAGE_LOCATION:
        raise ImproperlyConfigured("LINODE_PRIVATE_STORAGE_LOCATION must name a non-root prefix.")

    linode_storage_options = {
        "access_key": required_environment("LINODE_ACCESS_KEY_ID"),
        "secret_key": required_environment("LINODE_SECRET_ACCESS_KEY"),
        "bucket_name": required_environment("LINODE_STORAGE_BUCKET_NAME"),
        "endpoint_url": required_environment("LINODE_STORAGE_ENDPOINT"),
        "region_name": required_environment("LINODE_STORAGE_REGION"),
        "file_overwrite": False,
    }
    public_image_storage = {
        "BACKEND": "home.storage.ULIDS3Storage",
        "OPTIONS": {
            **linode_storage_options,
            "location": LINODE_STORAGE_LOCATION,
            "default_acl": os.environ.get(
                "LINODE_STORAGE_DEFAULT_ACL", "public-read"
            ),
            "querystring_auth": False,
        },
    }
    STORAGES["default"] = public_image_storage
    STORAGES["public_images"] = public_image_storage
    STORAGES["private_images"] = {
        "BACKEND": "home.storage.ULIDS3Storage",
        "OPTIONS": {
            **linode_storage_options,
            "location": LINODE_PRIVATE_STORAGE_LOCATION,
            "default_acl": "private",
            "querystring_auth": True,
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
