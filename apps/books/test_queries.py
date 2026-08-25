"""Sahifalar nechta SQL so'rov yuborishini qulflab qo'yadigan testlar.

Nega kerak: sekinlikning eng ko'p uchraydigan sababi — ro'yxatdagi har bir
element uchun qo'shimcha so'rov ketishi (N+1). Bu ko'zga tashlanmaydi:
sahifa ishlaydi, faqat sekin. Bitta kitob qo'shilsa 3 ta so'rov qo'shiladi.

Loyihada aynan shunday bo'lgan: bosh sahifa 26 ta so'rov yuborardi, chunki
shablonda `book.average_rating` ikki joyda ishlatilgan va har biri alohida
so'rov edi. `with_counts()` dan keyin 5 ta bo'ldi.

Quyidagi chegaralar shu holat qaytmasligi uchun. Agar test yiqilsa —
avval so'rovlar ro'yxatiga qarang, keyin chegarani ko'tarmang.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.books.models import Author, Book, Like, Review

User = get_user_model()


class QueryCountTests(TestCase):
    """Kitoblar soni oshsa ham so'rovlar soni oshmasligi kerak."""

    @classmethod
    def setUpTestData(cls):
        cls.seller = User.objects.create_user(
            username="sotuvchi", password="Parol-12345", role=Role.SELLER
        )
        cls.buyer = User.objects.create_user(
            username="xaridor", password="Parol-12345", role=Role.BUYER
        )
        author = Author.objects.create(full_name="Abdulla Qodiriy")

        # Bir nechta kitob: N+1 bo'lsa so'rovlar soni shu yerda ko'payadi.
        cls.books = [
            Book.objects.create(
                title=f"Kitob {i}",
                author=author,
                seller=cls.seller,
                pages=100,
                price=Decimal("45000"),
                language="uz",
            )
            for i in range(6)
        ]
        for book in cls.books:
            Review.objects.create(book=book, buyer=cls.buyer, rating=5, comment="Zo'r")
            Like.objects.create(book=book, user=cls.buyer)

    def setUp(self):
        cache.clear()

    def test_bosh_sahifa(self):
        with self.assertNumQueries(5):
            self.client.get(reverse("core:home"))

    def test_katalog(self):
        with self.assertNumQueries(4):
            self.client.get(reverse("books:catalog"))

    def test_kitob_sahifasi(self):
        with self.assertNumQueries(4):
            self.client.get(reverse("books:detail", args=[self.books[0].pk]))

    def test_kitob_qoshilsa_sorovlar_kopaymaydi(self):
        """Asosiy tekshiruv: ro'yxat uzaysa ham so'rovlar soni o'zgarmaydi."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        cache.clear()
        with CaptureQueriesContext(connection) as first:
            self.client.get(reverse("books:catalog"))

        author = Author.objects.create(full_name="Cho'lpon")
        for i in range(10):
            book = Book.objects.create(
                title=f"Yangi {i}",
                author=author,
                seller=self.seller,
                pages=50,
                price=Decimal("30000"),
                language="uz",
            )
            Review.objects.create(book=book, buyer=self.buyer, rating=4)
            Like.objects.create(book=book, user=self.buyer)

        cache.clear()
        with self.assertNumQueries(len(first.captured_queries)):
            self.client.get(reverse("books:catalog"))

    def test_reyting_togri_hisoblanadi(self):
        """Tezlashtirish natijani buzmasligi kerak.

        `Subquery` ishlatilishining sababi ham shu: bitta `annotate` ichida
        ikkita bog'lanish bo'yicha hisoblansa, SQL ularni ko'paytirib
        yuboradi va sonlar noto'g'ri chiqadi.
        """
        book = self.books[0]
        Review.objects.create(
            book=book,
            buyer=User.objects.create_user(username="ikkinchi", password="Parol-12345"),
            rating=3,
        )
        # Ikkinchi yoqtirish: reyting undan ta'sirlanmasligi kerak.
        Like.objects.create(
            book=book,
            user=User.objects.create_user(username="uchinchi", password="Parol-12345"),
        )

        annotated = Book.objects.with_counts().get(pk=book.pk)
        plain = Book.objects.get(pk=book.pk)

        self.assertEqual(annotated.average_rating, 4.0)  # (5 + 3) / 2
        self.assertEqual(annotated.average_rating, plain.average_rating)
        self.assertEqual(annotated.reviews_count, 2)
        self.assertEqual(annotated.likes_count, 2)
        self.assertEqual(annotated.reviews_count, plain.reviews_count)
        self.assertEqual(annotated.likes_count, plain.likes_count)

    def test_sharhsiz_kitob_nol_beradi(self):
        book = Book.objects.create(
            title="Sharhsiz",
            author=Author.objects.first(),
            seller=self.seller,
            pages=10,
            price=Decimal("1000"),
        )
        annotated = Book.objects.with_counts().get(pk=book.pk)
        self.assertEqual(annotated.average_rating, 0)
        self.assertEqual(annotated.reviews_count, 0)
        self.assertEqual(annotated.likes_count, 0)
