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


class AutoSetWebhookTests(TestCase):
    """Webhook server ko'tarilganda o'zi yoqilishi kerak.

    Render'ning bepul tarifida "Shell" yo'q — u yerda buyruqni qo'lda
    yozib bo'lmaydi. Shuning uchun bu avtomatik ishlashi shart, aks holda
    bot umuman javob bermaydi.
    """

    def setUp(self):
        self.calls = []

    def fake_call(self, method, payload=None, **kwargs):
        self.calls.append((method, payload))
        if method == "getWebhookInfo":
            return {"ok": True, "result": {"url": getattr(self, "current_url", "")}}
        return {"ok": True, "result": True}

    def run_hook(self):
        """Startup hookni chaqiradi va ip tugashini kutadi."""
        import threading

        from apps.core import apps as core_apps
        from apps.core import telegram

        before = set(threading.enumerate())
        original = telegram.call
        telegram.call = self.fake_call
        try:
            core_apps._auto_set_webhook()
            for thread in set(threading.enumerate()) - before:
                thread.join(timeout=5)
        finally:
            telegram.call = original

    def methods(self):
        return [method for method, _payload in self.calls]

    @override_settings(
        AUTO_SET_WEBHOOK=True, TELEGRAM_BOT_TOKEN=TOKEN, SITE_URL="https://sinov.onrender.com"
    )
    def test_webhook_avtomatik_yoqiladi(self):
        self.run_hook()

        self.assertIn("setWebhook", self.methods())
        payload = dict(self.calls)["setWebhook"]
        self.assertTrue(payload["url"].startswith("https://sinov.onrender.com/tg/"))
        self.assertTrue(payload["secret_token"])

    @override_settings(
        AUTO_SET_WEBHOOK=True, TELEGRAM_BOT_TOKEN=TOKEN, SITE_URL="https://sinov.onrender.com"
    )
    def test_allaqachon_ornatilgan_bolsa_qayta_yuborilmaydi(self):
        from apps.core.botlib.webhook import webhook_secret

        self.current_url = f"https://sinov.onrender.com/tg/{webhook_secret()}/"
        self.run_hook()

        self.assertNotIn("setWebhook", self.methods())

    @override_settings(AUTO_SET_WEBHOOK=False, TELEGRAM_BOT_TOKEN=TOKEN)
    def test_ochirilgan_bolsa_tegilmaydi(self):
        """Lokal ishlashda va testlarda hech qanday so'rov ketmasligi kerak."""
        self.run_hook()
        self.assertEqual(self.calls, [])

    @override_settings(AUTO_SET_WEBHOOK=True, TELEGRAM_BOT_TOKEN="")
    def test_tokensiz_holatda_tegilmaydi(self):
        self.run_hook()
        self.assertEqual(self.calls, [])

    @override_settings(
        AUTO_SET_WEBHOOK=True, TELEGRAM_BOT_TOKEN=TOKEN, SITE_URL="http://127.0.0.1:8000"
    )
    def test_https_bolmasa_yoqilmaydi(self):
        """Telegram webhook uchun faqat HTTPS manzilni qabul qiladi."""
        self.run_hook()
        self.assertEqual(self.calls, [])


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN)
class SetWebhookUrlTests(TestCase):
    """`set_webhook --url` ga to'liq havola berilsa ham to'g'ri manzil chiqsin.

    Foydalanuvchi brauzerdagi manzilni nusxalaganda unda ortiqcha yo'l
    bo'lishi tabiiy ("...onrender.com/kitoblar/"). Webhook esa sayt
    ildizidan boshlanishi shart, aks holda Telegram mavjud bo'lmagan
    sahifaga yozadi va bot jimgina javob bermay qoladi.
    """

    def call_command_with(self, url):
        from io import StringIO
        from unittest.mock import patch

        from django.core.management import call_command

        sent = {}

        def fake_call(method, payload=None, **kwargs):
            sent[method] = payload or {}
            return {"ok": True}

        out = StringIO()
        with patch("apps.core.telegram.call", side_effect=fake_call):
            call_command("set_webhook", url=url, stdout=out)
        return sent.get("setWebhook", {}).get("url", ""), out.getvalue()

    def test_ortiqcha_yol_tashlanadi(self):
        url, output = self.call_command_with("https://sayt.onrender.com/kitoblar/")
        self.assertRegex(url, r"^https://sayt\.onrender\.com/tg/[0-9a-f]{32}/$")
        self.assertIn("tashlandi", output)

    def test_toza_manzil_ozgarmaydi(self):
        url, _output = self.call_command_with("https://sayt.onrender.com")
        self.assertRegex(url, r"^https://sayt\.onrender\.com/tg/[0-9a-f]{32}/$")

    def test_oxiridagi_slesh_muammo_qilmaydi(self):
        url, _output = self.call_command_with("https://sayt.onrender.com/")
        self.assertRegex(url, r"^https://sayt\.onrender\.com/tg/[0-9a-f]{32}/$")
