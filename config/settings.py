# import os
# from pathlib import Path

# BASE_DIR = Path(__file__).resolve().parent.parent
# SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
# DEBUG = os.environ.get("DEBUG", "1") == "1"
# ALLOWED_HOSTS = [
#     "union-migrant-work2-1.onrender.com",
#     "localhost",
#     "127.0.0.1",
# ]
# CSRF_TRUSTED_ORIGINS = [
#     "https://union-migrant-work2-1.onrender.com",
# ]

# # import os
# # from pathlib import Path
# # from dotenv import load_dotenv

# # BASE_DIR = Path(__file__).resolve().parent.parent

# # # Загрузка переменных из .env
# # load_dotenv(BASE_DIR / ".env")

# # SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
# # DEBUG = os.environ.get("DEBUG", "0") == "1"

# # ALLOWED_HOSTS = [
# #     host.strip()
# #     for host in os.environ.get(
# #         "ALLOWED_HOSTS", "127.0.0.1,localhost"
# #     ).split(",")
# #     if host.strip()
# # ]

# # CSRF_TRUSTED_ORIGINS = [
# #     origin.strip()
# #     for origin in os.environ.get(
# #         "CSRF_TRUSTED_ORIGINS", ""
# #     ).split(",")
# #     if origin.strip()
# # ]



# INSTALLED_APPS = [
#     "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
#     "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
#     "core",
# ]
# MIDDLEWARE = [
#     "django.middleware.security.SecurityMiddleware",
#     "django.contrib.sessions.middleware.SessionMiddleware",
#     "django.middleware.common.CommonMiddleware",
#     "django.middleware.csrf.CsrfViewMiddleware",
#     "django.contrib.auth.middleware.AuthenticationMiddleware",
#     "django.contrib.messages.middleware.MessageMiddleware",
#     "core.middleware.LangMiddleware",
#     "django.middleware.clickjacking.XFrameOptionsMiddleware",
# ]
# ROOT_URLCONF = "config.urls"
# TEMPLATES = [{
#     "BACKEND": "django.template.backends.django.DjangoTemplates",
#     "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
#     "OPTIONS": {"context_processors": [
#         "django.template.context_processors.request",
#         "django.contrib.auth.context_processors.auth",
#         "django.contrib.messages.context_processors.messages",
#         "core.middleware.ui",
#     ]},
# }]
# WSGI_APPLICATION = "config.wsgi.application"

# # Своя база данных. По умолчанию SQLite; для PostgreSQL задайте DB_NAME, DB_USER, DB_PASSWORD, DB_HOST.
# if os.environ.get("DB_NAME"):
#     DATABASES = {"default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": os.environ["DB_NAME"], "USER": os.environ.get("DB_USER", ""),
#         "PASSWORD": os.environ.get("DB_PASSWORD", ""), "HOST": os.environ.get("DB_HOST", "localhost"),
#         "PORT": os.environ.get("DB_PORT", "5432"),
#     }}
# else:
#     DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

# AUTH_USER_MODEL = "core.User"
# AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}}]
# LANGUAGE_CODE = "ru"
# TIME_ZONE = "Europe/Moscow"
# USE_I18N = True
# USE_TZ = True
# STATIC_URL = "static/"
# STATICFILES_DIRS = [BASE_DIR / "static"]
# STATIC_ROOT = BASE_DIR / "staticfiles"
# MEDIA_URL = "media/"
# MEDIA_ROOT = BASE_DIR / "media"          # публичные фото: склады, сертификаты
# PRIVATE_ROOT = BASE_DIR / "private"      # документы и фото смен: только через проверку прав
# LOGIN_URL = "login"
# DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
# FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024






import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================
# SECURITY
# ==============================

ON_RENDER = bool(os.environ.get("RENDER"))

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")

DEBUG = os.environ.get("DEBUG", "0" if ON_RENDER else "1") == "1"

if ON_RENDER and SECRET_KEY == "dev-insecure-change-me":
    raise RuntimeError("Set a secure SECRET_KEY in Render Environment")

ALLOWED_HOSTS = [
    "union-migrant-work2-1.onrender.com",
    "localhost",
    "127.0.0.1",
]

render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)

CSRF_TRUSTED_ORIGINS = [
    "https://union-migrant-work2-1.onrender.com",
]

if render_hostname:
    render_origin = f"https://{render_hostname}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)

if ON_RENDER:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ==============================
# APPLICATIONS
# ==============================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

# ==============================
# MIDDLEWARE
# ==============================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "core.middleware.LangMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ==============================
# URLS AND TEMPLATES
# ==============================

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
                "core.middleware.ui",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ==============================
# DATABASE
# ==============================

DATABASE_URL = os.environ.get("DATABASE_URL")

if ON_RENDER and not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is required on Render. "
        "Connect your Render PostgreSQL database."
    )

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ==============================
# AUTHENTICATION
# ==============================

AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 6,
        },
    }
]

LOGIN_URL = "login"

# ==============================
# LANGUAGE AND TIME
# ==============================

LANGUAGE_CODE = "ru"

TIME_ZONE = "Europe/Moscow"

USE_I18N = True

USE_TZ = True

# ==============================
# STATIC FILES
# ==============================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static"
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

# ==============================
# MEDIA FILES
# ==============================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

# Local path only. Render's default filesystem
# is temporary. Configure persistent storage
# separately for uploaded files.
PRIVATE_ROOT = BASE_DIR / "private"

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ==============================
# OTHER SETTINGS
# ==============================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
