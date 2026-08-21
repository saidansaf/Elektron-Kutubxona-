"""Kitob fayli, o'qish va sotuvchi kabineti testlari.

Diqqat qaratilgan joy - pullik kontentga kim kira olishi. Bu yerda xato
qilinsa, kitoblar tekinga tarqalib ketadi.
"""

import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Role
from apps.books.models import (
    Author,
    Book,
    Conversation,
    Genre,
    Like,
    Message,
    Purchase,
    ReadingProgress,
    Review,
    Wish,
)
from apps.books.services import PurchaseError, purchase_book

User = get_user_model()

PDF_BYTES = b"%PDF-1.4 sinov kitobi"

# Sinov PDF'lari haqiqiy `private_media/` papkasiga tushmasligi uchun.
TEMP_PRIVATE_ROOT = tempfile.mkdtemp(prefix="kutubxona-test-")


class PrivateMediaTestCase(TestCase):
    """Fayl yozadigan testlar uchun asos: papka vaqtinchalik bo'ladi."""

    @classmethod
    def setUpClass(cls):
        cls._settings_override = override_settings(PRIVATE_MEDIA_ROOT=TEMP_PRIVATE_ROOT)
        cls._settings_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._settings_override.disable()
        shutil.rmtree(TEMP_PRIVATE_ROOT, ignore_errors=True)


def make_user(username, role=Role.BUYER, **extra):
    user = User.objects.create_user(username=username, password="parol12345", **extra)
    user.role = role
    user.save()
    return user


class BookFileAccessTests(PrivateMediaTestCase):
    """Kitob faylini kim ocha oladi."""

    @classmethod
    def setUpTestData(cls):
        cls.seller = make_user("sotuvchi", Role.SELLER)
        cls.buyer = make_user("xaridor", Role.BUYER)
        cls.stranger = make_user("begona", Role.BUYER)
        cls.admin = User.objects.create_superuser("admin", password="parol12345")

        author = Author.objects.create(full_name="Test Muallif")
        cls.book = Book.objects.create(
            title="Pullik kitob",
            author=author,
            seller=cls.seller,
            pages=10,
            price=Decimal("50000"),
        )
        cls.book.file.save("sinov.pdf", ContentFile(PDF_BYTES), save=True)
        Purchase.objects.create(buyer=cls.buyer, book=cls.book, price_paid=cls.book.price)

        cls.file_url = reverse("books:book_file", args=[cls.book.pk])
        cls.download_url = reverse("books:book_download", args=[cls.book.pk])
        cls.read_url = reverse("books:read", args=[cls.book.pk])

    def test_anonim_faylni_ololmaydi(self):
        response = self.client.get(self.file_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("kirish", response["Location"])

    def test_sotib_olmagan_foydalanuvchiga_404(self):
        """Ruxsati yo'q odamga 403 emas, 404 beriladi.

        403 "fayl bor, lekin sizga ruxsat yo'q" degani bo'lardi - begona
        odam kitobning fayli borligini ham bilmasligi kerak.
        """
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.file_url).status_code, 404)
        self.assertEqual(self.client.get(self.download_url).status_code, 404)
        self.assertEqual(self.client.get(self.read_url).status_code, 404)

    def test_sotib_olgan_xaridor_oladi(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.file_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), PDF_BYTES)

    def test_sotuvchi_oz_kitobini_oladi(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(self.file_url).status_code, 200)

    def test_administrator_oladi(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.file_url).status_code, 200)

    def test_yuklab_olish_fayl_sifatida_keladi(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.download_url)
        self.assertIn("attachment", response["Content-Disposition"])

    def test_oqish_uchun_brauzerda_ochiladi(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.file_url)
        self.assertIn("inline", response["Content-Disposition"])

    def test_fayl_media_papkasida_saqlanmaydi(self):
        """PDF ochiq beriladigan MEDIA_ROOT ichida turmasligi kerak."""
        from django.conf import settings

        stored = str(self.book.file.path)
        self.assertTrue(stored.startswith(str(settings.PRIVATE_MEDIA_ROOT)))
        self.assertFalse(stored.startswith(str(settings.MEDIA_ROOT)))

    def test_xususiy_fayl_manzili_faqat_xodimlarga(self):
        url = reverse("private_file", args=["book_files/sinov.pdf"])
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(url).status_code, 302)

        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)


class BookApiTests(PrivateMediaTestCase):
    """API pullik faylga havola bermasligi kerak."""

    @classmethod
    def setUpTestData(cls):
        cls.seller = make_user("sotuvchi", Role.SELLER)
        author = Author.objects.create(full_name="Test Muallif")
        cls.book = Book.objects.create(
            title="Pullik kitob", author=author, seller=cls.seller, pages=10, price=Decimal("50000")
        )
        cls.book.file.save("api-sinov.pdf", ContentFile(PDF_BYTES), save=True)

    def test_api_fayl_manzilini_bermaydi(self):
        response = self.client.get("/api/books/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["results"][0]
        self.assertNotIn("file", payload)
        self.assertTrue(payload["has_file"])
        self.assertNotIn("book_files", response.content.decode())


class ReadingProgressTests(PrivateMediaTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seller = make_user("sotuvchi", Role.SELLER)
        cls.buyer = make_user("xaridor", Role.BUYER)
        author = Author.objects.create(full_name="Test Muallif")
        cls.book = Book.objects.create(
            title="Kitob", author=author, seller=cls.seller, pages=10, price=Decimal("1000")
        )
        cls.book.file.save("progress.pdf", ContentFile(PDF_BYTES), save=True)
        Purchase.objects.create(buyer=cls.buyer, book=cls.book, price_paid=cls.book.price)
        cls.url = reverse("books:reading_progress", args=[cls.book.pk])

    def test_sahifa_saqlanadi(self):
        self.client.force_login(self.buyer)
        response = self.client.post(
            self.url, data={"page": 7, "total": 20}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        progress = ReadingProgress.objects.get(user=self.buyer, book=self.book)
        self.assertEqual(progress.page, 7)
        self.assertEqual(progress.percent, 35)
        self.assertFalse(progress.is_finished)

    def test_oxirgi_sahifa_tugallangan_deb_belgilanadi(self):
        self.client.force_login(self.buyer)
        self.client.post(self.url, data={"page": 20, "total": 20}, content_type="application/json")
        self.assertTrue(ReadingProgress.objects.get(user=self.buyer, book=self.book).is_finished)

    def test_sahifa_jami_sahifadan_oshib_ketmaydi(self):
        self.client.force_login(self.buyer)
        self.client.post(self.url, data={"page": 999, "total": 20}, content_type="application/json")
        self.assertEqual(ReadingProgress.objects.get(user=self.buyer, book=self.book).page, 20)

    def test_begona_odam_holat_saqlay_olmaydi(self):
        stranger = make_user("begona", Role.BUYER)
        self.client.force_login(stranger)
        response = self.client.post(
            self.url, data={"page": 3, "total": 20}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ReadingProgress.objects.filter(user=stranger).exists())


class SellerDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seller = make_user("sotuvchi", Role.SELLER)
        cls.buyer = make_user("xaridor", Role.BUYER)
        author = Author.objects.create(full_name="Test Muallif")

        cls.book = Book.objects.create(
            title="Birinchi", author=author, seller=cls.seller, pages=10, price=Decimal("45000")
        )
        cls.other = Book.objects.create(
            title="Ikkinchi", author=author, seller=cls.seller, pages=10, price=Decimal("62000")
        )

        # Uchta xarid + sharh va yoqtirishlar: agregatsiya ularni bir-biriga
        # ko'paytirib yubormasligini tekshiramiz.
        for i in range(3):
            buyer = make_user(f"oquvchi{i}", Role.BUYER)
            Purchase.objects.create(buyer=buyer, book=cls.book, price_paid=cls.book.price)
            Review.objects.create(book=cls.book, buyer=buyer, rating=4, comment="Zo'r")
            Like.objects.create(book=cls.book, user=buyer)

        cls.url = reverse("books:seller_dashboard")

    def test_xaridor_kabinetga_kira_olmaydi(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_sotuvchi_kabinetni_koradi(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_daromad_togri_hisoblanadi(self):
        """Sharh va yoqtirishlar summani ko'paytirib yubormasligi kerak.

        Bitta so'rovda JOIN orqali hisoblansa, 3 xarid x 3 sharh x 3
        yoqtirish = 27 qator chiqib, daromad to'qqiz barobar katta
        ko'rinardi.
        """
        self.client.force_login(self.seller)
        context = self.client.get(self.url).context

        self.assertEqual(context["revenue"], Decimal("135000"))  # 3 x 45000
        self.assertEqual(context["sales_count"], 3)
        self.assertEqual(context["buyers_count"], 3)

        by_title = {book.title: book for book in context["books"]}
        self.assertEqual(by_title["Birinchi"].revenue, Decimal("135000"))
        self.assertEqual(by_title["Birinchi"].sales_count, 3)
        self.assertEqual(by_title["Birinchi"].likes_total, 3)
        self.assertAlmostEqual(by_title["Birinchi"].avg_rating, 4.0)
        self.assertEqual(by_title["Ikkinchi"].revenue, Decimal("0"))

    def test_grafik_balandligi_butun_son(self):
        """CSS kasr sonni tushunmaydi (til qoidasi bo'yicha vergul qo'yiladi)."""
        self.client.force_login(self.seller)
        chart = self.client.get(self.url).context["chart"]
        self.assertEqual(len(chart), 30)
        for point in chart:
            self.assertIsInstance(point["height"], int)

    def test_savdo_hisoboti_excel_beriladi(self):
        self.client.force_login(self.seller)
        response = self.client.get(reverse("books:export_sales_excel"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])


class PurchaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seller = make_user("sotuvchi", Role.SELLER)
        cls.buyer = make_user("xaridor", Role.BUYER)
        cls.buyer.balance = Decimal("100000")
        cls.buyer.save()
        author = Author.objects.create(full_name="Test Muallif")
        cls.book = Book.objects.create(
            title="Kitob", author=author, seller=cls.seller, pages=10, price=Decimal("45000")
        )

    def _checkout(self, provider="payme"):
        """Kitobni karta orqali to'lash: buyurtma yaratiladi."""
        return self.client.post(
            reverse("books:buy", args=[self.book.pk]),
            {"address": "Toshkent, Chilonzor", "provider": provider},
        )

    def test_xarid_tolovdan_keyin_pulni_sotuvchiga_otkazadi(self):
        from apps.payments import testmode
        from apps.payments.models import Payment

        self.client.force_login(self.buyer)
        self.assertEqual(self._checkout().status_code, 302)

        # To'lov tasdiqlanmaguncha kitob berilmaydi.
        self.assertFalse(Purchase.objects.filter(buyer=self.buyer, book=self.book).exists())

        testmode.simulate_success(Payment.objects.get(user=self.buyer))

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.balance, Decimal("45000"))
        self.assertTrue(Purchase.objects.filter(buyer=self.buyer, book=self.book).exists())


class CatalogSortTests(TestCase):
    """Katalogda saralash."""

    @classmethod
    def setUpTestData(cls):
        seller = make_user("sotuvchi", Role.SELLER)
        author = Author.objects.create(full_name="Test Muallif")
        cls.cheap = Book.objects.create(
            title="Arzon", author=author, seller=seller, pages=10, price=Decimal("10000")
        )
        cls.expensive = Book.objects.create(
            title="Qimmat", author=author, seller=seller, pages=10, price=Decimal("90000")
        )
        buyer = make_user("xaridor", Role.BUYER)
        Review.objects.create(book=cls.expensive, buyer=buyer, rating=5, comment="Zo'r")
        Review.objects.create(book=cls.cheap, buyer=buyer, rating=2, comment="O'rtacha")

    def _titles(self, **params):
        response = self.client.get(reverse("books:catalog"), params)
        return [book.title for book in response.context["page_obj"]]

    def test_arzonidan_saralanadi(self):
        self.assertEqual(self._titles(sort="cheap")[0], "Arzon")

    def test_qimmatidan_saralanadi(self):
        self.assertEqual(self._titles(sort="expensive")[0], "Qimmat")

    def test_reyting_boyicha_saralanadi(self):
        self.assertEqual(self._titles(sort="rating")[0], "Qimmat")

    def test_notogri_qiymat_xato_bermaydi(self):
        response = self.client.get(reverse("books:catalog"), {"sort": "qwerty"})
        self.assertEqual(response.status_code, 200)

    def test_saralash_kesh_kalitiga_kiradi(self):
        """Aks holda arzon va qimmat tartibi bitta keshga tushib qolardi."""
        from django.test import RequestFactory

        from apps.books.views import _catalog_cache_key

        factory = RequestFactory()
        cheap = _catalog_cache_key(factory.get("/?sort=cheap"), 1)
        expensive = _catalog_cache_key(factory.get("/?sort=expensive"), 1)
        self.assertNotEqual(cheap, expensive)


class WishlistTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seller = make_user("sotuvchi", Role.SELLER)
        cls.buyer = make_user("xaridor", Role.BUYER)
        author = Author.objects.create(full_name="Test Muallif")
        cls.book = Book.objects.create(
            title="Kitob", author=author, seller=cls.seller, pages=10, price=Decimal("45000")
        )
        cls.url = reverse("books:toggle_wish", args=[cls.book.pk])

    def test_qoshiladi_va_olib_tashlanadi(self):
        self.client.force_login(self.buyer)

        self.client.post(self.url)
        self.assertTrue(Wish.objects.filter(user=self.buyer, book=self.book).exists())

        self.client.post(self.url)
        self.assertFalse(Wish.objects.filter(user=self.buyer, book=self.book).exists())

    def test_royxat_faqat_ozining_kitoblarini_korsatadi(self):
        boshqa = make_user("boshqa", Role.BUYER)
        Wish.objects.create(user=boshqa, book=self.book)

        self.client.force_login(self.buyer)
        response = self.client.get(reverse("books:wishlist"))
        self.assertEqual(len(response.context["wishes"]), 0)

    def test_anonim_qosha_olmaydi(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Wish.objects.exists())


class ConversationTests(TestCase):
    """Xaridor va sotuvchi xabarlashuvi."""

    @classmethod
    def setUpTestData(cls):
        cls.seller = make_user("sotuvchi", Role.SELLER)
        cls.buyer = make_user("xaridor", Role.BUYER)
        cls.stranger = make_user("begona", Role.BUYER)
        author = Author.objects.create(full_name="Test Muallif")
        cls.book = Book.objects.create(
            title="Kitob", author=author, seller=cls.seller, pages=10, price=Decimal("45000")
        )

    def _ask(self, text="Salom, savolim bor"):
        self.client.force_login(self.buyer)
        return self.client.post(
            reverse("books:conversation_start", args=[self.book.pk]), {"text": text}
        )

    def test_savol_suhbat_ochadi(self):
        self._ask()
        conversation = Conversation.objects.get()
        self.assertEqual(conversation.buyer, self.buyer)
        self.assertEqual(conversation.seller, self.seller)
        self.assertEqual(conversation.messages.count(), 1)

    def test_ikkinchi_savol_yangi_suhbat_ochmaydi(self):
        self._ask("Birinchi")
        self._ask("Ikkinchi")
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 2)

    def test_sotuvchi_ozi_bilan_suhbat_ocholmaydi(self):
        self.client.force_login(self.seller)
        self.client.post(reverse("books:conversation_start", args=[self.book.pk]), {"text": "?"})
        self.assertFalse(Conversation.objects.exists())

    def test_begona_odam_suhbatni_ocholmaydi(self):
        self._ask()
        conversation = Conversation.objects.get()

        self.client.force_login(self.stranger)
        response = self.client.get(reverse("books:conversation", args=[conversation.pk]))
        self.assertEqual(response.status_code, 404)

    def test_suhbat_ochilganda_xabarlar_oqilgan_deb_belgilanadi(self):
        self._ask()
        conversation = Conversation.objects.get()
        self.assertEqual(conversation.unread_count(self.seller), 1)

        self.client.force_login(self.seller)
        self.client.get(reverse("books:conversation", args=[conversation.pk]))
        self.assertEqual(conversation.unread_count(self.seller), 0)

    def test_ozining_xabari_oqilmagan_deb_sanalmaydi(self):
        self._ask()
        conversation = Conversation.objects.get()
        self.assertEqual(conversation.unread_count(self.buyer), 0)

    def test_bosh_xabar_saqlanmaydi(self):
        self._ask("   ")
        self.assertEqual(Message.objects.count(), 0)


class GenreCreateTests(TestCase):
    def setUp(self):
        self.seller = make_user("sotuvchi", Role.SELLER)
        self.buyer = make_user("xaridor", Role.BUYER)
        self.url = reverse("books:genre_create")

    def test_sotuvchi_janr_qosha_oladi(self):
        self.client.force_login(self.seller)
        self.client.post(self.url, {"name": "Ilmiy-fantastika"})
        self.assertTrue(Genre.objects.filter(name="Ilmiy-fantastika").exists())

    def test_xaridor_qosha_olmaydi(self):
        self.client.force_login(self.buyer)
        response = self.client.post(self.url, {"name": "Detektiv"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Genre.objects.filter(name="Detektiv").exists())


class PurchaseServiceTests(TestCase):
    """Sayt va bot uchun umumiy xarid funksiyasi.

    Mantiq ikki joyda takrorlanmasligi kerak: aks holda biri o'zgarganda
    ikkinchisi eskirib, pul hisobida farq paydo bo'ladi.
    """

    def setUp(self):
        self.seller = make_user("sotuvchi", Role.SELLER)
        self.buyer = make_user("xaridor", Role.BUYER)
        author = Author.objects.create(full_name="Test Muallif")
        self.book = Book.objects.create(
            title="Kitob", author=author, seller=self.seller, pages=10, price=Decimal("45000")
        )

    def test_pul_sotuvchiga_otadi(self):
        purchase = purchase_book(self.buyer, self.book)

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.balance, Decimal("45000"))
        self.assertEqual(purchase.price_paid, Decimal("45000"))
        # Xaridorda hisob yo'q — pul kartadan olingan.
        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.balance, Decimal("0"))

    def test_takroriy_xarid_bolmaydi(self):
        purchase_book(self.buyer, self.book)
        with self.assertRaises(PurchaseError):
            purchase_book(self.buyer, self.book)
        self.assertEqual(Purchase.objects.count(), 1)

    def test_ozining_kitobini_sotib_ololmaydi(self):
        with self.assertRaises(PurchaseError):
            purchase_book(self.seller, self.book)

    def test_sotuvdan_olingan_kitob_sotilmaydi(self):
        self.book.is_active = False
        self.book.save()
        with self.assertRaises(PurchaseError):
            purchase_book(self.buyer, self.book)

    def test_xarid_bekor_qilinsa_pul_qaytadi(self):
        """To'lov qaytarilganda sotuvchining daromadi ham qaytariladi."""
        from apps.books.services import cancel_purchase

        purchase = purchase_book(self.buyer, self.book)
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.balance, Decimal("45000"))

        cancel_purchase(purchase)

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.balance, Decimal("0"))
        self.assertFalse(Purchase.objects.exists())
