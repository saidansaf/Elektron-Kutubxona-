"""Telegram bot sozlamalarini tekshiradi.

    python manage.py check_bot

Token bormi, Telegram javob beradimi va nechta foydalanuvchi botni
ulaganini ko'rsatadi.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import TelegramLink
from apps.core import telegram


class Command(BaseCommand):
    help = "Telegram bot to'g'ri sozlanganini tekshiradi."

    def handle(self, *args, **options):
        ok = self.style.SUCCESS
        bad = self.style.ERROR
        warn = self.style.WARNING

        # 0. Kutubxona o'rnatilganmi
        self.stdout.write("0) Telegram kutubxonasi")
        try:
            import telebot  # noqa: F401
            from importlib.metadata import version

            self.stdout.write(ok(f"   pyTelegramBotAPI {version('pyTelegramBotAPI')}"))
        except ModuleNotFoundError:
            self.stdout.write(bad("   pyTelegramBotAPI o'rnatilmagan"))
            self.stdout.write("   Yechim:  pip install -r requirements.txt")
            return

        # 1. Token
        self.stdout.write("\n1) Bot tokeni")
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stdout.write(bad("   TELEGRAM_BOT_TOKEN bo'sh"))
            self.stdout.write("   Token olish:")
            self.stdout.write("     1. Telegram'da @BotFather ni oching")
            self.stdout.write("     2. /newbot yozing va nom bering")
            self.stdout.write("     3. Bergan tokenini .env ga qo'ying:")
            self.stdout.write("        TELEGRAM_BOT_TOKEN=123456:ABC-DEF...")
            self.stdout.write(warn("\n   Bot sozlanmagan, lekin sayt to'liq ishlayveradi."))
            return
        self.stdout.write(ok(f"   topildi: {token[:10]}...{token[-4:]}"))

        # 2. Telegram javob beradimi
        self.stdout.write("\n2) Telegram bilan aloqa")
        response = telegram.call("getMe")
        if not response or not response.get("ok"):
            self.stdout.write(bad("   javob olinmadi"))
            self.stdout.write("   Internet ulanishini va tokenning to'g'riligini tekshiring.")
            return

        me = response["result"]
        self.stdout.write(ok(f"   @{me.get('username')} ({me.get('first_name')})"))

        if not settings.TELEGRAM_BOT_USERNAME:
            self.stdout.write(
                warn(f"   .env ga qo'shing: TELEGRAM_BOT_USERNAME={me.get('username')}")
            )

        # 2b. Webhook holati
        self.stdout.write("\n2b) Webhook holati")
        hook = telegram.call("getWebhookInfo")
        result = (hook or {}).get("result", {})
        hook_url = result.get("url", "")

        from apps.core.botlib.webhook import webhook_secret

        expected = f"{settings.SITE_URL.rstrip('/')}/tg/{webhook_secret()}/"

        if not hook_url:
            self.stdout.write("   webhook yo'q (long polling rejimi)")
            self.stdout.write("   Lokal ishlash uchun to'g'ri:  python manage.py bot")
            self.stdout.write("   Serverda esa webhook kerak:   python manage.py set_webhook")
        elif hook_url == expected:
            self.stdout.write(ok(f"   yoqilgan: {hook_url}"))
        else:
            self.stdout.write(warn(f"   yoqilgan, lekin boshqa manzilga: {hook_url}"))
            self.stdout.write(f"   kutilgani: {expected}")
            self.stdout.write("   SITE_URL to'g'rimi? Qayta yoqish: python manage.py set_webhook")

        if result.get("last_error_message"):
            self.stdout.write(bad(f"   Telegram xatosi: {result['last_error_message']}"))
            self.stdout.write("   (bu xato saytga yuborilgan oxirgi so'rovda chiqqan)")
        if result.get("pending_update_count"):
            self.stdout.write(
                warn(f"   Kutayotgan yangiliklar: {result['pending_update_count']}")
            )

        # 3. Ulangan foydalanuvchilar
        self.stdout.write("\n3) Ulangan foydalanuvchilar")
        linked = TelegramLink.objects.filter(chat_id__isnull=False).select_related("user")
        if not linked:
            self.stdout.write("   hali hech kim ulanmagan")
            self.stdout.write("   Ulash: saytda Sozlamalar -> Telegram bot -> Kod olish")
        else:
            for link in linked[:10]:
                mark = "🔔" if link.notifications else "🔕"
                self.stdout.write(ok(f"   {mark} {link.user.username}"))
            self.stdout.write(f"   jami: {linked.count()}")

        # 4. Sayt manzili
        self.stdout.write("\n4) Botdagi havolalar manzili")
        self.stdout.write(f"   SITE_URL = {settings.SITE_URL}")
        if "127.0.0.1" in settings.SITE_URL or "localhost" in settings.SITE_URL:
            self.stdout.write(
                warn("   Bu lokal manzil - botdagi havolalar boshqa qurilmada ochilmaydi.")
            )

        self.stdout.write(ok("\nBotni ishga tushirish:  python manage.py bot"))
