"""Kesh sozlamalarini tekshiradi.

    python manage.py check_cache

Redis ulanganmi, yozib-o'qib bo'ladimi va kontent versiyasi ishlayaptimi -
ketma-ket tekshirib, muammo qayerdaligini aytadi.
"""

import time

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.core.cache import CONTENT_VERSION_KEY, bump_content_version, content_version, rate_limit


class Command(BaseCommand):
    help = "Kesh (Redis yoki xotira) to'g'ri ishlayotganini tekshiradi."

    def handle(self, *args, **options):
        ok = self.style.SUCCESS
        bad = self.style.ERROR
        warn = self.style.WARNING

        backend = settings.CACHES["default"]["BACKEND"]
        is_redis = "redis" in backend.lower()

        # 1. Qaysi backend ishlatilyapti
        self.stdout.write("1) Kesh turi")
        if is_redis:
            self.stdout.write(ok(f"   Redis: {settings.REDIS_URL}"))
        else:
            self.stdout.write(warn("   Xotiradagi kesh (LocMemCache)"))
            self.stdout.write(
                "   Redis ulash uchun .env ga qo'ying:  REDIS_URL=redis://127.0.0.1:6379/1"
            )
            self.stdout.write("   Redis'siz ham loyiha to'liq ishlaydi - kesh faqat sekinroq.")

        # 2. Yozish va o'qish
        self.stdout.write("\n2) Yozish/o'qish")
        probe_key = "check-cache-probe"
        probe_value = f"sinov-{time.time()}"
        try:
            cache.set(probe_key, probe_value, 30)
            read = cache.get(probe_key)
        except Exception as exc:
            self.stdout.write(bad(f"   ULANIB BO'LMADI: {exc}"))
            if is_redis:
                self.stdout.write("   Redis ishga tushganini tekshiring:  redis-cli ping")
                self.stdout.write("   Yoki .env dagi REDIS_URL qatorini o'chirib qo'ying.")
            return

        if read == probe_value:
            self.stdout.write(ok("   yozildi va qaytib o'qildi"))
        else:
            self.stdout.write(bad(f"   qiymat mos kelmadi: {read!r}"))
            return
        cache.delete(probe_key)

        # 3. Kontent versiyasi
        self.stdout.write("\n3) Kontent versiyasi (keshni yangilash uchun)")
        before = content_version()
        after = bump_content_version()
        self.stdout.write(f"   {CONTENT_VERSION_KEY}: {before} -> {after}")
        if after > before:
            self.stdout.write(ok("   versiya oshdi - kitob o'zgarganda kesh yangilanadi"))
        else:
            self.stdout.write(bad("   versiya oshmadi"))

        # 4. So'rovlar chegarasi
        self.stdout.write("\n4) AI so'rovlari chegarasi")
        self.stdout.write(
            f"   xabarlar: {settings.AI_RATE_LIMIT_MESSAGES} ta / "
            f"{settings.AI_RATE_LIMIT_WINDOW // 60} daqiqa"
        )
        self.stdout.write(
            f"   rasmlar:  {settings.AI_RATE_LIMIT_IMAGES} ta / "
            f"{settings.AI_RATE_LIMIT_WINDOW // 60} daqiqa"
        )
        allowed, left = rate_limit("check-cache", "sinov", 3, 10)
        if allowed:
            self.stdout.write(ok(f"   hisoblagich ishlayapti (qoldi: {left})"))
        else:
            self.stdout.write(bad("   hisoblagich ishlamadi"))
        cache.delete("rate:check-cache:sinov")

        # 5. Sessiyalar
        self.stdout.write("\n5) Sessiyalar")
        engine = getattr(settings, "SESSION_ENGINE", "django.contrib.sessions.backends.db")
        if "cached_db" in engine:
            self.stdout.write(ok("   keshdan o'qiladi, bazaga zaxira sifatida yoziladi"))
        else:
            self.stdout.write("   faqat bazada saqlanadi")

        # 6. Keshlanadigan sahifalar
        self.stdout.write("\n6) Keshlanadigan sahifalar")
        self.stdout.write(f"   bosh sahifa: {settings.CACHE_TIMEOUT_HOME} soniya")
        self.stdout.write(f"   katalog:     {settings.CACHE_TIMEOUT_CATALOG} soniya")

        self.stdout.write(ok("\nKesh ishlayapti."))
