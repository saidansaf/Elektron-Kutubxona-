"""Telegram webhook'ini yoqadi yoki o'chiradi.

    python manage.py set_webhook            # yoqadi (SITE_URL bo'yicha)
    python manage.py set_webhook --off      # o'chiradi (polling'ga qaytish)
    python manage.py set_webhook --status   # hozirgi holatni ko'rsatadi

Webhook yoqilgach bot alohida jarayonsiz ishlaydi: Telegram yangilikni
saytga o'zi yuboradi. Render kabi xizmatlarda aynan shu kerak.

Muhim: webhook va `manage.py bot` (long polling) birga ishlay olmaydi.
Bittasini tanlash kerak — aks holda Telegram 409 Conflict qaytaradi.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core import telegram
from apps.core.botlib.webhook import webhook_secret


class Command(BaseCommand):
    help = "Telegram webhook'ini yoqadi, o'chiradi yoki holatini ko'rsatadi."

    def add_arguments(self, parser):
        parser.add_argument("--off", action="store_true", help="Webhook'ni o'chiradi.")
        parser.add_argument("--status", action="store_true", help="Holatni ko'rsatadi.")
        parser.add_argument(
            "--url",
            default="",
            help="Sayt manzili (bo'sh bo'lsa SITE_URL ishlatiladi).",
        )

    def handle(self, *args, **options):
        ok = self.style.SUCCESS
        bad = self.style.ERROR
        warn = self.style.WARNING

        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError(
                "TELEGRAM_BOT_TOKEN sozlanmagan. .env faylga tokenni qo'ying."
            )

        if options["status"]:
            info = telegram.call("getWebhookInfo") or {}
            result = info.get("result", {})
            url = result.get("url", "")
            if url:
                self.stdout.write(ok(f"Webhook yoqilgan:\n  {url}"))
                pending = result.get("pending_update_count", 0)
                if pending:
                    self.stdout.write(warn(f"  Kutayotgan yangiliklar: {pending}"))
                if result.get("last_error_message"):
                    self.stdout.write(bad(f"  Oxirgi xato: {result['last_error_message']}"))
            else:
                self.stdout.write("Webhook o'chirilgan (long polling rejimi).")
            return

        if options["off"]:
            response = telegram.call("deleteWebhook", {"drop_pending_updates": True})
            if response and response.get("ok"):
                self.stdout.write(ok("Webhook o'chirildi. Endi: python manage.py bot"))
            else:
                self.stdout.write(bad("Webhook'ni o'chirib bo'lmadi."))
            return

        raw = (options["url"] or settings.SITE_URL).strip()
        if not raw.startswith("https://"):
            shown = raw or "(bo'sh)"
            raise CommandError(
                "Webhook faqat HTTPS manzilda ishlaydi.\n"
                f"  Hozirgi manzil: {shown}\n"
                "  Lokal kompyuterda ishlayotgan bo'lsangiz webhook kerak emas —\n"
                "  oddiygina `python manage.py bot` ni ishlating."
            )

        # Manzildan faqat domen olinadi. Foydalanuvchi brauzerdagi to'liq
        # havolani nusxalab qo'yishi tabiiy ("...onrender.com/kitoblar/"),
        # lekin webhook manzili sayt ILDIZIDAN boshlanishi shart — aks holda
        # Telegram mavjud bo'lmagan sahifaga yozadi va bot jim qoladi.
        from urllib.parse import urlparse

        parsed = urlparse(raw)
        site = f"{parsed.scheme}://{parsed.netloc}"
        if parsed.path.strip("/"):
            self.stdout.write(
                warn(f"Manzildagi ortiqcha qism tashlandi: /{parsed.path.strip('/')}")
            )

        secret = webhook_secret()
        url = f"{site}/tg/{secret}/"

        response = telegram.call(
            "setWebhook",
            {
                "url": url,
                "secret_token": secret,
                "drop_pending_updates": True,
                "allowed_updates": ["message", "callback_query"],
            },
        )
        if response and response.get("ok"):
            self.stdout.write(ok("Webhook yoqildi."))
            self.stdout.write(f"  Manzil: {url}")
            self.stdout.write("\nEndi bot saytning ichida ishlaydi — alohida jarayon kerak emas.")
            self.stdout.write("Tekshirish:  python manage.py set_webhook --status")
        else:
            description = (response or {}).get("description", "javob olinmadi")
            raise CommandError(f"Webhook o'rnatilmadi: {description}")
