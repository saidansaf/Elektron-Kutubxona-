"""Webhook rejimi testlari.

Webhook — Render kabi xizmatlarda botning yagona ishlash yo'li: u yerda
"doim ishlab turadigan ikkinchi jarayon" bepul tarifda berilmaydi.
Shuning uchun bu yo'l ishlashi va begonaga ochiq bo'lmasligi muhim.
"""

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, TelegramLink
from apps.books.models import Author, Book

User = get_user_model()

TOKEN = "123456:SINOV-TOKEN"


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN)
class WebhookSecurityTests(TestCase):
    """Manzilni topgan begona odam botga soxta xabar yubora olmasin."""

    def setUp(self):
        from apps.core.botlib import webhook

        webhook._bot = None  # har testda toza boshlansin
        self.secret = webhook.webhook_secret()
        self.url = f"/tg/{self.secret}/"

    def post(self, url=None, secret_header=None, body=None):
        return self.client.post(
            url or self.url,
            data=json.dumps(body or {"update_id": 1}),
            content_type="application/json",
            **({"HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN": secret_header} if secret_header else {}),
        )

    def test_notogri_manzil_404(self):
        response = self.post(url="/tg/yolgon-so'z/", secret_header=self.secret)
        self.assertEqual(response.status_code, 404)

    def test_sarlavhasiz_sorov_404(self):
        """Manzilni bilgan bo'lsa ham, Telegram sarlavhasi bo'lmasa rad etiladi."""
        response = self.post()
        self.assertEqual(response.status_code, 404)

    def test_notogri_sarlavha_404(self):
        response = self.post(secret_header="boshqa-so'z")
        self.assertEqual(response.status_code, 404)

    def test_get_sorovi_qabul_qilinmaydi(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_togri_sorov_qabul_qilinadi(self):
        response = self.post(secret_header=self.secret)
        self.assertEqual(response.status_code, 200)

    def test_buzuq_json_ham_200_qaytaradi(self):
        """Aks holda Telegram xuddi shu xabarni cheksiz qayta yuboraveradi."""
        response = self.client.post(
            self.url,
            data="bu json emas",
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=self.secret,
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(TELEGRAM_BOT_TOKEN="")
    def test_token_yoq_bolsa_manzil_ishlamaydi(self):
        response = self.post(secret_header=self.secret)
        self.assertEqual(response.status_code, 404)


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN)
class WebhookFlowTests(TestCase):
    """Webhook orqali kelgan xabar haqiqiy handlerga yetib boradimi."""

    CHAT = 777001

    def setUp(self):
        from apps.core.botlib import webhook

        webhook._bot = None
        self.webhook = webhook
        self.secret = webhook.webhook_secret()
        self.url = f"/tg/{self.secret}/"

        self.seller = User.objects.create_user(username="sotuvchi", password="x", role=Role.SELLER)
        self.buyer = User.objects.create_user(
            username="xaridor", password="x", role=Role.BUYER, balance=Decimal("500000")
        )
        self.author = Author.objects.create(full_name="Abdulla Qodiriy")
        self.book = Book.objects.create(
            title="Otkan kunlar", author=self.author, seller=self.seller,
            pages=100, price=Decimal("45000"),
        )
        TelegramLink.objects.create(user=self.buyer, chat_id=self.CHAT, linked_at=timezone.now())

    def send(self, text):
        """Telegram yuboradigan yangilik ko'rinishidagi so'rov."""
        payload = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "date": 0,
                "chat": {"id": self.CHAT, "type": "private"},
                "from": {"id": self.CHAT, "is_bot": False, "first_name": "T", "username": "tg"},
                "text": text,
            },
        }
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=self.secret,
        )

    def test_xabar_handlerga_yetib_boradi(self):
        sent = []
        bot = self.webhook.get_bot()
        self.assertIsNotNone(bot, "Bot yaratilmadi")
        bot.send_message = lambda chat_id, text, **kw: sent.append(text)

        response = self.send("📚 Katalog")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(sent, "Bot javob bermadi")
        self.assertIn("Otkan kunlar", sent[-1])

    def test_bot_obyekti_qayta_ishlatiladi(self):
        """Har so'rovda handlerlarni qaytadan ro'yxatdan o'tkazish ortiqcha."""
        first = self.webhook.get_bot()
        second = self.webhook.get_bot()
        self.assertIs(first, second)
