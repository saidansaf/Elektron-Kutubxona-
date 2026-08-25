"""Kesh, kesh invalidatsiyasi va AI so'rovlari chegarasi testlari.

Testlar Redis talab qilmaydi: Django'ning xotiradagi keshi ham xuddi shu
interfeysni beradi, shuning uchun mantiq ikkalasida bir xil tekshiriladi.
"""

import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Role
from apps.books.models import Author, Book
from apps.core.cache import bump_content_version, content_version, rate_limit, rate_limit_state

User = get_user_model()

LOCMEM = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}


@override_settings(CACHES=LOCMEM)
class ContentVersionTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_versiya_boshlangich_qiymatga_ega(self):
        self.assertEqual(content_version(), 1)

    def test_versiya_oshadi(self):
        first = content_version()
        self.assertEqual(bump_content_version(), first + 1)
        self.assertEqual(content_version(), first + 1)

    def test_kesh_tozalansa_ham_ishlaydi(self):
        bump_content_version()
        cache.clear()
        # Xato bermasligi kerak - kalit yo'q bo'lsa qaytadan yaratiladi.
        self.assertEqual(content_version(), 1)


@override_settings(CACHES=LOCMEM)
class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_chegaragacha_ruxsat_beriladi(self):
        for expected_left in (2, 1, 0):
            allowed, left = rate_limit("sinov", "user-1", 3, 60)
            self.assertTrue(allowed)
            self.assertEqual(left, expected_left)

    def test_chegaradan_keyin_taqiqlanadi(self):
        for _ in range(3):
            rate_limit("sinov", "user-1", 3, 60)
        allowed, left = rate_limit("sinov", "user-1", 3, 60)
        self.assertFalse(allowed)
        self.assertEqual(left, 0)

    def test_foydalanuvchilar_bir_biriga_tasir_qilmaydi(self):
        for _ in range(3):
            rate_limit("sinov", "user-1", 3, 60)
        allowed, _left = rate_limit("sinov", "user-2", 3, 60)
        self.assertTrue(allowed)

    def test_turli_bolimlar_alohida_sanaladi(self):
        for _ in range(3):
            rate_limit("chat", "user-1", 3, 60)
        allowed, _left = rate_limit("rasm", "user-1", 3, 60)
        self.assertTrue(allowed)

    def test_holat_hisoblagichni_oshirmaydi(self):
        rate_limit("sinov", "user-1", 5, 60)
        self.assertEqual(rate_limit_state("sinov", "user-1", 5), 4)
        self.assertEqual(rate_limit_state("sinov", "user-1", 5), 4)


@override_settings(CACHES=LOCMEM, AI_RATE_LIMIT_MESSAGES=2, AI_RATE_LIMIT_IMAGES=1)
class AiRateLimitViewTests(TestCase):
    """Chegara AI so'rovlarida ham qo'llanishi kerak."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="oquvchi", password="parol12345")
        self.client.force_login(self.user)

    def _send(self):
        return self.client.post(
            reverse("core:ai_send"),
            data={"message": "salom"},
            content_type="application/json",
        )

    def test_chegaradan_oshsa_429_qaytariladi(self):
        # AI kaliti sozlanmagan bo'lsa ham chegara tekshiruvi undan oldin
        # ishlaydi, shuning uchun javob kodi 429 bo'lishi kerak.
        self._send()
        self._send()
        response = self._send()
        self.assertEqual(response.status_code, 429)
        self.assertIn("error", response.json())

    def test_rasm_generatsiyasi_olib_tashlangan(self):
        """Muqova rasmini AI yasashi olib tashlandi.

        Sababi: natija kitobga hech qanday aloqasi yo'q rasm bo'lardi va
        chegarani bekorga sarflardi. Manzil ham qolmasligi kerak.
        """
        from django.urls import NoReverseMatch

        with self.assertRaises(NoReverseMatch):
            reverse("core:ai_image")

    def test_bosh_xabar_chegarani_sarflamaydi(self):
        response = self.client.post(
            reverse("core:ai_send"), data={"message": "   "}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(rate_limit_state("ai-chat", self.user.pk, 2), 2)


# Ataylab yopiq port: shu manzilga ulanib bo'lmaydi.
BROKEN_REDIS = {
    "default": {
        "BACKEND": "apps.core.cache_backend.ResilientRedisCache",
        "LOCATION": "redis://127.0.0.1:63999/0",
        "KEY_PREFIX": "kutubxona-test",
        "OPTIONS": {"socket_timeout": 1, "socket_connect_timeout": 1},
    }
}


@override_settings(CACHES=BROKEN_REDIS)
class RedisDownTests(TestCase):
    """Redis o'chib qolsa sayt ishlashda davom etishi kerak.

    Kesh - tezlik uchun qo'shimcha vosita, u yo'q bo'lgani uchun sahifa
    500 xatosi bermasligi kerak.
    """

    @classmethod
    def setUpTestData(cls):
        seller = User.objects.create_user(username="sotuvchi", password="parol12345")
        seller.role = Role.SELLER
        seller.save()
        author = Author.objects.create(full_name="Test Muallif")
        Book.objects.create(
            title="Kitob", author=author, seller=seller, pages=10, price=Decimal("45000")
        )

    def setUp(self):
        # Kesh ishlamagani haqidagi ogohlantirishlar test natijasini
        # to'sib qo'ymasligi uchun.
        logging.disable(logging.WARNING)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_bosh_sahifa_ochiladi(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kitob")

    def test_katalog_ochiladi(self):
        self.assertEqual(self.client.get(reverse("books:catalog")).status_code, 200)

    def test_versiya_xato_bermaydi(self):
        self.assertIsInstance(content_version(), int)
        self.assertIsInstance(bump_content_version(), int)

    def test_chegara_foydalanuvchini_bloklamaydi(self):
        """Kesh ishlamasa chegara tekshirilmaydi, lekin kirish yopilmaydi."""
        for _ in range(10):
            allowed, _left = rate_limit("sinov", "user-1", 2, 60)
            self.assertTrue(allowed)


@override_settings(CACHES=LOCMEM)
class PageCacheTests(TestCase):
    """Bosh sahifa va katalog keshlanishi va o'z vaqtida yangilanishi."""

    @classmethod
    def setUpTestData(cls):
        cls.seller = User.objects.create_user(username="sotuvchi", password="parol12345")
        cls.seller.role = Role.SELLER
        cls.seller.save()
        cls.author = Author.objects.create(full_name="Test Muallif")
        cls.book = Book.objects.create(
            title="Birinchi kitob",
            author=cls.author,
            seller=cls.seller,
            pages=10,
            price=Decimal("45000"),
        )

    def setUp(self):
        cache.clear()

    def test_bosh_sahifa_ikkinchi_marta_bazaga_bormaydi(self):
        self.client.get(reverse("core:home"))
        with self.assertNumQueries(0):
            response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Birinchi kitob")

    def test_yangi_kitob_qoshilsa_kesh_yangilanadi(self):
        self.client.get(reverse("core:home"))

        Book.objects.create(
            title="Ikkinchi kitob",
            author=self.author,
            seller=self.seller,
            pages=20,
            price=Decimal("50000"),
        )

        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Ikkinchi kitob")

    def test_kitob_ochirilsa_kesh_yangilanadi(self):
        self.client.get(reverse("core:home"))
        self.book.delete()
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "Birinchi kitob")

    def test_katalog_keshlanadi(self):
        first = self.client.get(reverse("books:catalog"))
        second = self.client.get(reverse("books:catalog"))
        self.assertContains(first, "Birinchi kitob")
        self.assertContains(second, "Birinchi kitob")

    def test_turli_filtrlar_alohida_keshlanadi(self):
        """Filtrlangan natija boshqa filtrning keshini egallab olmasligi kerak."""
        Book.objects.create(
            title="Ruscha kitob",
            author=self.author,
            seller=self.seller,
            pages=20,
            price=Decimal("50000"),
            language="ru",
        )

        uz_page = self.client.get(reverse("books:catalog"), {"language": "uz"})
        ru_page = self.client.get(reverse("books:catalog"), {"language": "ru"})

        self.assertContains(uz_page, "Birinchi kitob")
        self.assertNotContains(uz_page, "Ruscha kitob")
        self.assertContains(ru_page, "Ruscha kitob")
        self.assertNotContains(ru_page, "Birinchi kitob")

    def test_filtr_tartibi_keshga_tasir_qilmaydi(self):
        """`?a=1&b=2` va `?b=2&a=1` bir xil kesh yozuviga tushishi kerak."""
        from apps.books.views import _catalog_cache_key
        from django.test import RequestFactory

        factory = RequestFactory()
        first = _catalog_cache_key(factory.get("/?language=uz&q=kitob"), 1)
        second = _catalog_cache_key(factory.get("/?q=kitob&language=uz"), 1)
        self.assertEqual(first, second)
