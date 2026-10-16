import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    "union-migrant-work2-1.onrender.com",
    "localhost",
    "127.0.0.1",
]
CSRF_TRUSTED_ORIGINS = [
    "https://union-migrant-work2-1.onrender.com",
]

# import os
# from pathlib import Path
# from dotenv import load_dotenv

# BASE_DIR = Path(__file__).resolve().parent.parent

# # Загрузка переменных из .env
# load_dotenv(BASE_DIR / ".env")

# SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
# DEBUG = os.environ.get("DEBUG", "0") == "1"

# ALLOWED_HOSTS = [
#     host.strip()
#     for host in os.environ.get(
#         "ALLOWED_HOSTS", "127.0.0.1,localhost"
#     ).split(",")
#     if host.strip()
# ]

# CSRF_TRUSTED_ORIGINS = [
#     origin.strip()
#     for origin in os.environ.get(
#         "CSRF_TRUSTED_ORIGINS", ""
#     ).split(",")
#     if origin.strip()
# ]



INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "core",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "core.middleware.LangMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "core.middleware.ui",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

# Своя база данных. По умолчанию SQLite; для PostgreSQL задайте DB_NAME, DB_USER, DB_PASSWORD, DB_HOST.
if os.environ.get("DB_NAME"):
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"], "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""), "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_USER_MODEL = "core.User"
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}}]
LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"          # публичные фото: склады, сертификаты
PRIVATE_ROOT = BASE_DIR / "private"      # документы и фото смен: только через проверку прав
LOGIN_URL = "login"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
