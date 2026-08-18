"""Kesh bilan ishlash: kontent versiyasi va so'rovlar chegarasi.

Loyiha Redis'siz ham ishlaydi - u holda Django'ning xotiradagi keshi
qo'llanadi. Shuning uchun bu yerdagi hamma narsa keshning yo'qolib
qolishiga chidamli bo'lishi kerak: kesh bo'shalsa, eng yomoni sahifa
qaytadan hisoblanadi.
"""

from django.core.cache import cache

CONTENT_VERSION_KEY = "content-version"

# Chegarani sanashda ishlatiladigan kalit prefiksi
RATE_LIMIT_PREFIX = "rate"


def content_version():
    """Keshlangan sahifalarning joriy versiyasi.

    Kitob, sharh yoki yoqtirish o'zgarganda bu raqam oshadi va shu bilan
    barcha eski keshlangan fragmentlar avtomatik "eskirgan" bo'lib qoladi -
    ularni birma-bir o'chirish shart emas.
    """
    version = cache.get(CONTENT_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(CONTENT_VERSION_KEY, version, None)
    return version


def bump_content_version():
    """Keshlangan sahifalarni eskirgan deb belgilaydi."""
    try:
        return cache.incr(CONTENT_VERSION_KEY)
    except ValueError:
        # Kalit hali yo'q edi (yoki kesh tozalangan).
        cache.set(CONTENT_VERSION_KEY, 1, None)
        return 1


def rate_limit(scope, identifier, limit, window):
    """So'rovlar sonini cheklaydi.

    `(ruxsat_berildi, qolgan_soni)` juftligini qaytaradi. Oyna (window)
    birinchi so'rovdan boshlanadi va tugagach hisob noldan boshlanadi.

    Kesh ishlamay qolsa chegara tekshirilmaydi - foydalanuvchini bloklab
    qo'ygandan ko'ra o'tkazib yuborgan afzal.
    """
    if limit <= 0:
        return True, 0

    key = f"{RATE_LIMIT_PREFIX}:{scope}:{identifier}"
    try:
        used = cache.get_or_set(key, 0, window)
        if used is None:
            return True, limit
        if used >= limit:
            return False, 0
        try:
            used = cache.incr(key)
        except ValueError:
            cache.set(key, 1, window)
            used = 1
    except Exception:
        return True, limit

    return True, max(0, limit - used)


def rate_limit_state(scope, identifier, limit):
    """Chegarani oshirmasdan, qolgan so'rovlar sonini qaytaradi."""
    if limit <= 0:
        return 0
    try:
        used = cache.get(f"{RATE_LIMIT_PREFIX}:{scope}:{identifier}") or 0
    except Exception:
        return limit
    return max(0, limit - used)
