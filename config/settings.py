"""
Django settings for Elektron Kutubxona (e-book marketplace) project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# utf-8-sig: Windows Bloknoti saqlaganda qo'shiladigan BOM belgisini tashlab yuboradi.
load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig")

# PostgreSQL xato xabarlarini ingliz tilida olish. Rus/o'zbek tilidagi Windows'da
# libpq xabarni cp1251 kodlashda qaytaradi va psycopg2 uni UTF-8 deb o'qishga
# urinib, asl sababni yashiradigan UnicodeDecodeError beradi.
os.environ.setdefault("LC_MESSAGES", "C")


def env_bool(key, default=False):
    value = os.environ.get(key)
    if value is None:
        return default
    # Bloknot va shunga o'xshash muharrirlar qo'shib yuborishi mumkin bo'lgan
    # qo'shtirnoq, bo'shliq va BOM belgilarini tozalaymiz.
    value = value.strip().strip("\"'").strip().lstrip("﻿")
    return value.lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-CHANGE-THIS-IN-PRODUCTION")

DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()
]
# Codespaces/cloud-preview kabi muhitlarda ishlashi uchun:
ALLOWED_HOSTS += [".githubpreview.dev", ".app.github.dev"]

# --- Render.com ---
#
# Render xizmat manzilini RENDER_EXTERNAL_HOSTNAME o'zgaruvchisiga o'zi
# yozib qo'yadi. Uni qo'lda ALLOWED_HOSTS ga kiritishni unutish - deploydan
# keyingi eng ko'p uchraydigan xato (sayt "Bad Request (400)" beradi).
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)

# Django 4+ da HTTPS orqali kelgan POST so'rovlar uchun domen ro'yxatda
# bo'lishi shart, aks holda har bir forma "CSRF verification failed" beradi.
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]
if RENDER_HOST:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOST}")

if not DEBUG:
    # Nginx/Render HTTPS'ni o'zi hal qiladi va Django'ga oddiy HTTP orqali
    # uzatadi. Bu sarlavhasiz Django "men HTTP'daman" deb o'ylab, cheksiz
    # yo'naltirish halqasiga tushib qoladi.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", 31536000))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # 3rd party
    "rest_framework",
    "django_filters",
    # local apps
    "apps.accounts",
    "apps.books",
    "apps.core",
    "apps.payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Statik fayllarni (CSS, JS, PDF.js) Django'ning o'zi beradi. Render'da
    # Nginx yo'q, shuning uchun busiz sayt uslubsiz - qip-yalang'och HTML
    # bo'lib ochiladi.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # HTML/JSON javoblarni siqadi. Sahifalarimiz matnga to'la - siqilgach
    # hajmi 4-5 barobar kichrayadi va sekin internetda seziladigan darajada
    # tez ochiladi. WhiteNoise'dan KEYIN turibdi: statik fayllar (rasm,
    # shrift) unga yetib kelmaydi, ya'ni bekorga qayta siqilmaydi.
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.UserPreferencesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_preferences",
                "apps.core.context_processors.admin_messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

def _database_from_url(url):
    """`postgres://user:parol@host:port/baza` ni Django lug'atiga aylantiradi.

    Render, Railway va shunga o'xshash xizmatlar bazani aynan shu ko'rinishda
    beradi — bitta DATABASE_URL o'zgaruvchisi bilan. Buning uchun alohida
    kutubxona (dj-database-url) o'rnatish shart emas, o'n qator kod yetadi.
    """
    from urllib.parse import unquote, urlparse

    parsed = urlparse(url)
    return {
        "ENGINE": "apps.core.db.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
        # Render bazasi tashqi tarmoqda — shifrlangan ulanish talab qiladi.
        "OPTIONS": {"sslmode": os.environ.get("DB_SSLMODE", "require")},
        # Har so'rovda yangi ulanish ochilmasin (bepul tarifda sezilarli).
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", 600)),
    }


DATABASE_URL = (os.environ.get("DATABASE_URL") or "").strip().strip("\"'")

if DATABASE_URL:
    DATABASES = {"default": _database_from_url(DATABASE_URL)}
elif env_bool("USE_SQLITE", False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    db_engine = os.environ.get("DB_ENGINE", "django.db.backends.postgresql")
    # Standart PostgreSQL backend'ini o'z qobig'imizga almashtiramiz: u ulanish
    # xatolarini o'qiladigan qilib ko'rsatadi (apps/core/db/postgresql/base.py).
    if db_engine == "django.db.backends.postgresql":
        db_engine = "apps.core.db.postgresql"

    DATABASES = {
        "default": {
            "ENGINE": db_engine,
            "NAME": os.environ.get("DB_NAME", "kutubxona_db"),
            "USER": os.environ.get("DB_USER", "kutubxona_user"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "kutubxona_pass123"),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }


AUTH_USER_MODEL = "accounts.User"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("uz", "O'zbekcha"),
    ("ru", "Русский"),
    ("en", "English"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# Sayt UI tilini custom middleware orqali ham boshqaramiz (sozlamalar sahifasi).
SUPPORTED_UI_LANGUAGES = ["uz", "ru", "en"]
BOOK_LANGUAGES = [
    ("uz", "O'zbekcha"),
    ("ru", "Русский"),
    ("en", "English"),
]


# Static & media files

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise fayllarni siqadi va nomiga hash qo'shadi (uzoq muddatli kesh).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Pullik kontent (kitob PDF fayllari).
#
# MEDIA_ROOT ichidagi hamma narsa internetga ochiq beriladi, shuning uchun
# sotiladigan kitoblar u yerda turmaydi. Ular alohida papkada saqlanadi va
# faqat ruxsatni tekshiradigan view orqali uzatiladi (apps/books/views.py).
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"
PRIVATE_MEDIA_URL = "/xususiy-fayl/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Auth redirects

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "core:home"


# REST Framework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}


# Administrator bilan bog'lanish havolasi (sozlamalar sahifasida ko'rinadi)
ADMIN_TELEGRAM_URL = os.environ.get("ADMIN_TELEGRAM_URL", "https://t.me/Saidansaf001")

# --- Sun'iy intellekt (AI) ---
# Bepul API kalitlari: qaysi biri to'ldirilgan bo'lsa, o'sha ishlatiladi.
#   Gemini     -> https://aistudio.google.com/apikey
#   Groq       -> https://console.groq.com/keys
#   OpenRouter -> https://openrouter.ai/keys
def env_str(key, default=""):
    """Qiymatni tozalab oladi: ortiqcha bo'shliq, qo'shtirnoq va BOM tashlanadi."""
    return (os.environ.get(key) or default).strip().strip("\"'").strip().lstrip("\ufeff")


AI_PROVIDER = env_str("AI_PROVIDER", "gemini").lower()
AI_API_KEY = env_str("AI_API_KEY")
AI_MODEL = env_str("AI_MODEL")
# Rasm generatsiyasi: standart holda Pollinations - kalit talab qilmaydi.
AI_IMAGE_PROVIDER = os.environ.get("AI_IMAGE_PROVIDER", "pollinations")

# Boshlang'ich admin (seed_admin buyrug'i orqali yaratiladi)
ADMIN_SEED_USERNAME = os.environ.get("ADMIN_USERNAME", "Saidansaf")
ADMIN_SEED_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD", "@saidansaf.com123googlebu_meni_kuchli_parolim"
)
ADMIN_SEED_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@kutubxona.uz")

# Serverda administrator parolini tiklash uchun.
#
# `seed_admin` parolni faqat hisob birinchi marta yaratilganda o'rnatadi.
# Bu bayroq yoqilsa, mavjud hisobning paroli ham ADMIN_PASSWORD ga
# tenglashtiriladi. Render kabi xizmatlarda terminal bo'lmagani uchun
# parolni tiklashning boshqa yo'li yo'q.
#
# Tiklangandan keyin o'chirib qo'yish kerak — aks holda har deploydan
# keyin parol qaytadan tiklanaveradi.
ADMIN_RESET_PASSWORD = env_bool("ADMIN_RESET_PASSWORD", False)

# Xaridorga ro'yxatdan o'tganda beriladigan boshlang'ich hamyon balansi (so'm)
DEFAULT_BUYER_BALANCE = 500000

# --- Email (parolni tiklash uchun) ---
# Gmail bilan: https://myaccount.google.com/apppasswords dan "App password"
# olib, EMAIL_HOST_USER va EMAIL_HOST_PASSWORD ga yozing.
EMAIL_HOST = env_str("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(env_str("EMAIL_PORT", "587") or 587)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = env_str("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env_str("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env_str("DEFAULT_FROM_EMAIL") or (EMAIL_HOST_USER or "no-reply@kutubxona.uz")

# SMTP sozlanmagan bo'lsa xat konsolga chiqadi va loyiha baribir ishlayveradi.
EMAIL_CONFIGURED = bool(EMAIL_HOST_USER and EMAIL_HOST_PASSWORD)
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_CONFIGURED
    else "django.core.mail.backends.console.EmailBackend"
)

# Hisobni to'ldirish chegaralari (so'm)
TOPUP_MIN = 1000
TOPUP_MAX = 10_000_000

# Sotuvchi balansdan pul yechish uchun so'raydigan eng kam summa
WITHDRAWAL_MIN = 10_000


# --- To'lov tizimlari (Payme / Click) ---
#
# Ikki rejim bor:
#
#   PAYMENT_MODE=test  — standart. Provayder saytiga chiqilmaydi, o'zimizdagi
#                        to'lov sahifasi ochiladi. Kalit kerak emas, lekin
#                        protokol kodi haqiqiy yo'ldan o'tadi.
#   PAYMENT_MODE=live  — haqiqiy Payme/Click. Kalitlar to'ldirilgan bo'lishi
#                        shart, aks holda tegishli tugma ko'rinmaydi.
#
# Kalitlar shartnomadan keyin beriladi (batafsil: docs/TOLOV.md).
PAYMENT_MODE = env_str("PAYMENT_MODE", "test").lower()

PAYME_MERCHANT_ID = env_str("PAYME_MERCHANT_ID")
PAYME_KEY = env_str("PAYME_KEY")
PAYME_CHECKOUT_URL = env_str("PAYME_CHECKOUT_URL", "https://checkout.paycom.uz")
# Payme kabinetida buyurtma raqami qaysi nom bilan yuborilishi ko'rsatiladi.
PAYME_ACCOUNT_FIELD = env_str("PAYME_ACCOUNT_FIELD", "order_id")

CLICK_SERVICE_ID = env_str("CLICK_SERVICE_ID")
CLICK_MERCHANT_ID = env_str("CLICK_MERCHANT_ID")
CLICK_SECRET_KEY = env_str("CLICK_SECRET_KEY")
CLICK_CHECKOUT_URL = env_str("CLICK_CHECKOUT_URL", "https://my.click.uz/services/pay")

if PAYMENT_MODE != "live":
    # Test rejimida ham imzo va parol tekshiruvi haqiqiy ishlashi kerak,
    # aks holda o'sha kod hech qachon sinovdan o'tmaydi va kalit kelgan
    # kuni xatolar birinchi marta jonli to'lovda chiqadi. Shuning uchun
    # kalitlarni SECRET_KEY dan hosil qilamiz - hech qayerga yozish
    # shart emas, lekin qiymati bor.
    import hashlib as _hashlib

    def _test_key(name):
        return _hashlib.sha256(f"{name}:{SECRET_KEY}".encode()).hexdigest()[:32]

    PAYME_KEY = PAYME_KEY or _test_key("payme")
    CLICK_SECRET_KEY = CLICK_SECRET_KEY or _test_key("click")
    PAYME_MERCHANT_ID = PAYME_MERCHANT_ID or "test-merchant"
    CLICK_SERVICE_ID = CLICK_SERVICE_ID or "test-service"
    CLICK_MERCHANT_ID = CLICK_MERCHANT_ID or "test-merchant"


# --- Kesh (Redis ixtiyoriy) ---
#
# `.env` da REDIS_URL berilsa Redis ishlatiladi, berilmasa - Django'ning
# xotiradagi standart keshi. Ya'ni Redis o'rnatilmagan kompyuterda ham
# loyiha hech qanday o'zgarishsiz ishlayveradi.
REDIS_URL = env_str("REDIS_URL")
CACHE_ENABLED = bool(REDIS_URL)

if CACHE_ENABLED:
    CACHES = {
        "default": {
            # Standart RedisCache emas: bizniki ulanish uzilganda xatoni
            # yuqoriga uzatmaydi, sahifa oddiy holicha bazadan hisoblanadi.
            "BACKEND": "apps.core.cache_backend.ResilientRedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "kutubxona",
            "OPTIONS": {"socket_timeout": 2, "socket_connect_timeout": 2},
        }
    }
    # Sessiyalar avval keshdan qidiriladi, topilmasa bazadan olinadi.
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "kutubxona-locmem",
        }
    }

# Keshda saqlash muddati (soniya)
CACHE_TIMEOUT_HOME = int(env_str("CACHE_TIMEOUT_HOME", "300") or 300)
CACHE_TIMEOUT_CATALOG = int(env_str("CACHE_TIMEOUT_CATALOG", "180") or 180)


# --- AI so'rovlari chegarasi ---
#
# Bepul API kalitlarining kunlik limiti bor. Chegara bo'lmasa bitta
# foydalanuvchi uni bir o'zi tugatib qo'yishi mumkin.
AI_RATE_LIMIT_MESSAGES = int(env_str("AI_RATE_LIMIT_MESSAGES", "30") or 30)
AI_RATE_LIMIT_IMAGES = int(env_str("AI_RATE_LIMIT_IMAGES", "10") or 10)
AI_RATE_LIMIT_WINDOW = int(env_str("AI_RATE_LIMIT_WINDOW", "3600") or 3600)


# --- Telegram bot ---
#
# Token @BotFather dan olinadi. Bo'sh bo'lsa bot ishga tushmaydi, lekin
# sayt hech qanday o'zgarishsiz ishlayveradi - bildirishnomalar shunchaki
# yuborilmaydi.
TELEGRAM_BOT_TOKEN = env_str("TELEGRAM_BOT_TOKEN")

# Server ko'tarilganda webhook o'zi yoqilsinmi (apps/core/apps.py).
# Render'da 1 qilinadi: u yerda bepul tarifda "Shell" yo'q va webhook'ni
# qo'lda yoqib bo'lmaydi. Lokal ishlashda 0 - polling ishlatiladi.
AUTO_SET_WEBHOOK = env_bool("AUTO_SET_WEBHOOK", False)
TELEGRAM_BOT_USERNAME = env_str("TELEGRAM_BOT_USERNAME")

# Botdagi havolalar shu manzilga olib boradi
# Botdagi havolalar shu manzilga olib boradi. Render'da domenni qo'lda
# yozish shart emas — xizmat manzili o'zi ma'lum.
SITE_URL = env_str("SITE_URL").rstrip("/")
if not SITE_URL:
    SITE_URL = f"https://{RENDER_HOST}" if RENDER_HOST else "http://127.0.0.1:8000"
