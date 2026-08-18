"""Redis o'chib qolsa ham yiqilmaydigan kesh.

Django'ning standart `RedisCache` backend'i ulanish uzilganda xatoni
yuqoriga uzatadi va sahifa 500 xatosi bilan tugaydi. Kesh esa tezlik
uchun qo'shimcha vosita, u yo'q bo'lgani uchun sayt ishlamay qolmasligi
kerak.

Bu qobiq ulanish xatolarini yutadi va ularni oddiy "keshda topilmadi"
holati sifatida ko'rsatadi - sahifa shunchaki bazadan qaytadan
hisoblanadi.
"""

import logging

from django.core.cache.backends.redis import RedisCache

logger = logging.getLogger(__name__)

try:  # redis paketi o'rnatilmagan bo'lishi ham mumkin
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover
    RedisError = ()

# Ulanish uzilishi OSError ko'rinishida ham kelishi mumkin
CACHE_ERRORS = (RedisError, OSError) if RedisError else (OSError,)


class ResilientRedisCache(RedisCache):
    """Xatolarni yutadigan Redis backend'i."""

    def _safe(self, operation, default, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except CACHE_ERRORS as exc:
            logger.warning("Kesh ishlamadi (%s): %s", operation.__name__, exc)
            return default

    def get(self, key, default=None, version=None):
        return self._safe(super().get, default, key, default, version)

    def set(self, key, value, timeout=None, version=None, client=None):
        return self._safe(super().set, None, key, value, timeout, version)

    def add(self, key, value, timeout=None, version=None):
        # False = "qo'shilmadi", chaqiruvchi buni tabiiy holat deb qabul qiladi
        return self._safe(super().add, False, key, value, timeout, version)

    def touch(self, key, timeout=None, version=None):
        return self._safe(super().touch, False, key, timeout, version)

    def delete(self, key, version=None):
        return self._safe(super().delete, False, key, version)

    def get_many(self, keys, version=None):
        return self._safe(super().get_many, {}, keys, version)

    def set_many(self, data, timeout=None, version=None):
        return self._safe(super().set_many, [], data, timeout, version)

    def delete_many(self, keys, version=None):
        return self._safe(super().delete_many, None, keys, version)

    def has_key(self, key, version=None):
        return self._safe(super().has_key, False, key, version)

    def incr(self, key, delta=1, version=None):
        # ValueError (kalit yo'q) chaqiruvchi tomonda ushlanadi, shuning
        # uchun uni yutmaymiz - faqat ulanish xatolarini yutamiz.
        try:
            return super().incr(key, delta, version)
        except CACHE_ERRORS as exc:
            logger.warning("Kesh ishlamadi (incr): %s", exc)
            raise ValueError("kesh mavjud emas") from exc

    def clear(self):
        return self._safe(super().clear, None)
