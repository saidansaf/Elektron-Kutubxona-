"""Balans, pul yechish va rollar bilan bog'liq testlar."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, TelegramLink, Withdrawal
from apps.books.models import Author, Book

User = get_user_model()


def make_user(username, role=Role.BUYER, balance="0"):
    user = User.objects.create_user(username=username, password="parol12345")
    user.role = role
    user.balance = Decimal(balance)
    user.save()
    return user


class WithdrawalRequestTests(TestCase):
    """Sotuvchining pul yechish so'rovi."""

    def setUp(self):
        self.seller = make_user("sotuvchi", Role.SELLER, "500000")
        self.url = reverse("accounts:withdrawal")
        self.client.force_login(self.seller)

    def _request(self, amount="150000"):
        return self.client.post(
            self.url, {"amount": amount, "card_number": "8600123456789012"}
        )

    def test_sorov_summani_balansdan_ushlab_qoladi(self):
        """Aks holda bir pulni bir necha marta so'rash mumkin bo'lardi."""
        self._request("150000")

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.balance, Decimal("350000"))

        withdrawal = Withdrawal.objects.get(seller=self.seller)
        self.assertEqual(withdrawal.amount, Decimal("150000"))
        self.assertTrue(withdrawal.is_pending)

    def test_balansdan_kop_sorab_bolmaydi(self):
        self._request("900000")

        self.assertFalse(Withdrawal.objects.exists())
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.balance, Decimal("500000"))

    def test_juda_kichik_summa_qabul_qilinmaydi(self):
        self._request("500")
        self.assertFalse(Withdrawal.objects.exists())

    def test_ikkinchi_sorov_yuborib_bolmaydi(self):
        self._request("100000")
        self._request("100000")

        self.assertEqual(Withdrawal.objects.count(), 1)
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.balance, Decimal("400000"))

    def test_xaridor_pul_yecha_olmaydi(self):
        buyer = make_user("xaridor", Role.BUYER, "500000")
        self.client.force_login(buyer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_karta_raqami_maskalanadi(self):
        self._request("100000")
        self.assertEqual(Withdrawal.objects.get().card_masked, "**** 9012")


class WithdrawalDecisionTests(TestCase):
    """Administrator so'rovni ko'rib chiqadi."""

    def setUp(self):
        self.seller = make_user("sotuvchi", Role.SELLER, "500000")
        self.admin = User.objects.create_superuser("admin", password="parol12345")

        self.client.force_login(self.seller)
        self.client.post(
            reverse("accounts:withdrawal"),
            {"amount": "150000", "card_number": "8600123456789012"},
        )
        self.withdrawal = Withdrawal.objects.get()
        self.url = reverse("core:admin_withdrawal_decide", args=[self.withdrawal.pk])
        self.client.force_login(self.admin)

    def test_tasdiqlanganda_balans_ozgarmaydi(self):
        """Pul so'rov paytida yechilgan edi - ikkinchi marta yechilmasin."""
        self.client.post(self.url, {"decision": "approve"})

        self.withdrawal.refresh_from_db()
        self.seller.refresh_from_db()
        self.assertEqual(self.withdrawal.status, Withdrawal.Status.APPROVED)
        self.assertEqual(self.seller.balance, Decimal("350000"))

    def test_rad_etilganda_pul_qaytariladi(self):
        self.client.post(self.url, {"decision": "reject", "comment": "Karta xato"})

        self.withdrawal.refresh_from_db()
        self.seller.refresh_from_db()
        self.assertEqual(self.withdrawal.status, Withdrawal.Status.REJECTED)
        self.assertEqual(self.withdrawal.comment, "Karta xato")
        self.assertEqual(self.seller.balance, Decimal("500000"))

    def test_ikki_marta_tasdiqlab_bolmaydi(self):
        self.client.post(self.url, {"decision": "approve"})
        self.client.post(self.url, {"decision": "reject"})

        self.withdrawal.refresh_from_db()
        self.seller.refresh_from_db()
        self.assertEqual(self.withdrawal.status, Withdrawal.Status.APPROVED)
        self.assertEqual(self.seller.balance, Decimal("350000"))

    def test_oddiy_foydalanuvchi_qaror_qila_olmaydi(self):
        self.client.force_login(self.seller)
        self.client.post(self.url, {"decision": "approve"})

        self.withdrawal.refresh_from_db()
        self.assertTrue(self.withdrawal.is_pending)

    def test_sorovlar_royxati_faqat_administratorga(self):
        url = reverse("core:admin_withdrawals")

        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(url).status_code, 302)

        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)


class NoWalletTests(TestCase):
    """Xaridorda hisob (balans) yo'q.

    Ilgari ro'yxatdan o'tganda 500 000 so'm "sovg'a balans" berilardi va
    alohida "Hisobni to'ldirish" sahifasi bor edi. Endi har bir kitob
    karta orqali alohida to'lanadi, shuning uchun ikkalasi ham olib
    tashlangan.
    """

    def setUp(self):
        self.buyer = make_user("xaridor", Role.BUYER, "0")
        self.client.force_login(self.buyer)

    def test_hisob_toldirish_sahifasi_yoq(self):
        from django.urls import NoReverseMatch

        with self.assertRaises(NoReverseMatch):
            reverse("accounts:topup")

    def test_rol_tanlash_bepul_balans_bermaydi(self):
        user = make_user("yangi-xaridor", Role.NONE, "0")
        self.client.force_login(user)
        self.client.post(reverse("accounts:role_select"), {"role": Role.BUYER})

        user.refresh_from_db()
        self.assertEqual(user.role, Role.BUYER)
        self.assertEqual(user.balance, Decimal("0"))

    def test_sozlamalarda_xaridorga_balans_korsatilmaydi(self):
        response = self.client.get(reverse("accounts:settings"))
        self.assertNotContains(response, "Daromadingiz")


class TelegramLinkTests(TestCase):
    """Saytdagi hisobni Telegram bilan bog'lash."""

    def setUp(self):
        self.user = make_user("oquvchi", Role.BUYER)
        self.client.force_login(self.user)
        self.url = reverse("accounts:telegram")

    def test_kod_olinadi(self):
        self.client.post(self.url)
        link = TelegramLink.objects.get(user=self.user)
        self.assertEqual(len(link.code), 6)
        self.assertTrue(link.code.isdigit())
        self.assertTrue(link.code_is_fresh())

    def test_yangi_kod_eskisini_almashtiradi(self):
        self.client.post(self.url)
        first = TelegramLink.objects.get(user=self.user).code
        self.client.post(self.url)
        second = TelegramLink.objects.get(user=self.user).code
        self.assertNotEqual(first, second)

    def test_eskirgan_kod_ishlamaydi(self):
        """Muddatsiz kod bilan hisobni egallab olish mumkin bo'lardi."""
        link = TelegramLink.objects.create(
            user=self.user, code="123456", code_created_at=timezone.now() - timedelta(hours=2)
        )
        self.assertFalse(link.code_is_fresh())

    def test_uzish_chat_id_ni_tozalaydi(self):
        TelegramLink.objects.create(user=self.user, chat_id=555, linked_at=timezone.now())
        self.client.post(self.url, {"action": "unlink"})

        link = TelegramLink.objects.get(user=self.user)
        self.assertIsNone(link.chat_id)
        self.assertFalse(link.is_linked)

    def test_bildirishnomalarni_ochirish(self):
        TelegramLink.objects.create(user=self.user, chat_id=555)
        self.client.post(self.url, {"action": "notifications"})
        self.assertFalse(TelegramLink.objects.get(user=self.user).notifications)

    def test_anonim_kira_olmaydi(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


class TelegramNotifyTests(TestCase):
    """Bildirishnomalar: token yo'q bo'lsa ham sayt ishlashi kerak."""

    def setUp(self):
        self.user = make_user("oquvchi", Role.BUYER)

    def test_token_yoq_bolsa_xato_bermaydi(self):
        from apps.core import telegram

        with override_settings(TELEGRAM_BOT_TOKEN=""):
            self.assertIsNone(telegram.notify(self.user, "salom"))

    def test_ulanmagan_foydalanuvchiga_yuborilmaydi(self):
        from apps.core import telegram

        TelegramLink.objects.create(user=self.user)  # chat_id yo'q
        with override_settings(TELEGRAM_BOT_TOKEN="sinov"):
            self.assertIsNone(telegram.notify(self.user, "salom"))

    def test_ochirilgan_bildirishnoma_yuborilmaydi(self):
        from apps.core import telegram

        TelegramLink.objects.create(user=self.user, chat_id=555, notifications=False)
        with override_settings(TELEGRAM_BOT_TOKEN="sinov"):
            self.assertIsNone(telegram.notify(self.user, "salom"))


class RegisterOnPurchaseTests(TestCase):
    """Katalog va kitob sahifasi hammaga ochiq; ro'yxatdan o'tish faqat
    sotib olmoqchi bo'lganda so'raladi va keyin o'sha kitobga qaytariladi."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username="sotuvchi2", password="x", role=Role.SELLER
        )
        self.author = Author.objects.create(full_name="Cho'lpon")
        self.book = Book.objects.create(
            title="Kecha va kunduz",
            author=self.author,
            seller=self.seller,
            pages=120,
            price=Decimal("38000"),
        )

    def test_katalog_kirmasdan_ochiladi(self):
        response = self.client.get(reverse("books:catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kecha va kunduz")

    def test_kitob_malumotlari_kirmasdan_ochiladi(self):
        response = self.client.get(reverse("books:detail", args=[self.book.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kecha va kunduz")

    def test_kirmagan_foydalanuvchiga_royxatdan_otish_taklif_qilinadi(self):
        response = self.client.get(reverse("books:detail", args=[self.book.pk]))
        self.assertContains(response, reverse("accounts:register"))

    def test_sotib_olish_kirishni_talab_qiladi(self):
        response = self.client.get(reverse("books:buy", args=[self.book.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_royxatdan_otgach_kitobga_qaytariladi(self):
        book_url = reverse("books:detail", args=[self.book.pk])

        self.client.get(f"{reverse('accounts:register')}?next={book_url}")
        self.client.post(
            reverse("accounts:register"),
            {
                "username": "yangi",
                "email": "yangi@example.com",
                "password1": "Juda-Kuchli-Parol-99",
                "password2": "Juda-Kuchli-Parol-99",
                "next": book_url,
            },
        )
        # Rol tanlanmaguncha bosh sahifaga emas, rol tanlashga boradi.
        response = self.client.post(reverse("accounts:role_select"), {"role": Role.BUYER})
        self.assertRedirects(response, book_url)

    def test_begona_saytga_yonaltirmaydi(self):
        """`next` bilan boshqa saytga olib chiqib bo'lmasligi kerak."""
        self.client.get(f"{reverse('accounts:register')}?next=https://evil.example/")
        self.client.post(
            reverse("accounts:register"),
            {
                "username": "yangi2",
                "email": "yangi2@example.com",
                "password1": "Juda-Kuchli-Parol-99",
                "password2": "Juda-Kuchli-Parol-99",
            },
        )
        response = self.client.post(reverse("accounts:role_select"), {"role": Role.BUYER})
        self.assertRedirects(response, reverse("core:home"))
