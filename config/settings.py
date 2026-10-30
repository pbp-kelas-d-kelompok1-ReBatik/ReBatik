
"""
Django settings for config project.
"""

import os
import re
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv



# BASE CONFIGURATION


BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

load_dotenv(BASE_DIR / ".env")



# SECURITY


SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY must be set in the environment or .env file."
    )


def get_environment_bool(name, default="False"):
    """Read and validate boolean environment variables."""
    value = os.getenv(name, default).strip().lower()

    if value in {"true", "1", "yes"}:
        return True

    if value in {"false", "0", "no"}:
        return False

    raise ImproperlyConfigured(
        f"{name} must be true/false, 1/0, or yes/no."
    )


DEBUG = get_environment_bool("DEBUG")
PRODUCTION = get_environment_bool("PRODUCTION")

CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "").strip()

if PRODUCTION and not CLOUDINARY_URL:
    raise ImproperlyConfigured(
        "CLOUDINARY_URL must be set when PRODUCTION=True."
    )


ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "alisa-selvia-rebatik.pws.cs.ui.ac.id",
]

CSRF_TRUSTED_ORIGINS = [
    "https://alisa-selvia-rebatik.pws.cs.ui.ac.id",
]



# APPLICATIONS


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # ReBatik applications
    "main",
    "marketplace",
    "upcycling",
    "rewards",
    "batik_story",
    "donasi",
    "batik_custom",
    "impact_tracker",
    "profiles",
    "landing",
]



# MIDDLEWARE


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]



# URL AND TEMPLATES


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

                # Custom context processors
                "upcycling.context_processors.upcycling_navigation",
                "main.context_processors.notification_count",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"



# DATABASE


if PRODUCTION:
    required_database_variables = (
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_PORT",
        "SCHEMA",
    )

    missing_variables = [
        name
        for name in required_database_variables
        if not os.getenv(name)
    ]

    if missing_variables:
        raise ImproperlyConfigured(
            "Missing production database variables: "
            + ", ".join(missing_variables)
        )

    schema = os.getenv("SCHEMA")

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
        raise ImproperlyConfigured(
            "SCHEMA must be a valid PostgreSQL schema name."
        )

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT"),
            "OPTIONS": {
                "options": f"-c search_path={schema}",
            },
        }
    }

else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }



# PASSWORD VALIDATION


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]

# Mempercepat pembuatan user selama automated testing.
# Hanya aktif ketika menjalankan perintah test.
if "test" in sys.argv:
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]



# INTERNATIONALIZATION


LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Jakarta"

USE_I18N = True

USE_TZ = True



UPCYCLING_FABRIC_DEADLINE_DAYS = 7


STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

WHITENOISE_USE_FINDERS = True

WHITENOISE_MIMETYPES = {
    ".jpe": "image/jpeg",
    ".webp": "image/webp",
}

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"



STORAGES = {
    "default": {
        "BACKEND": (
            "config.storage_backends.CloudinaryMediaStorage"
            if PRODUCTION
            else "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}


# Email console backend: email ditampilkan di terminal.
# Cocok untuk development dan testing.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"



LOGIN_URL = "main:login"
