"""Telegram bot.

    python manage.py bot

Bot saytning ikkinchi yuzi: **xuddi shu ma'lumotlar bazasi** bilan
ishlaydi, o'z bazasi yo'q. Shuning uchun botda qilingan ish saytda,
saytda qilingan ish botda darrov ko'rinadi.

Bu fayl faqat botni ishga tushiradi. Handlerlar va klaviaturalar
`apps/core/botlib/` ichida — u yerda ular mavzular bo'yicha ajratilgan
va alohida test qilinadi.
"""

import logging

try:
    import telebot
except ModuleNotFoundError as exc:  # pragma: no cover - o'rnatish xatosi
    raise SystemExit(
        "Telegram kutubxonasi o'rnatilmagan.\n"
        "  Yechim:  pip install pyTelegramBotAPI\n"
        "  yoki:    pip install -r requirements.txt"
    ) from exc

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import TelegramLink
from apps.core.botlib.handlers import register_handlers  # noqa: F401 (testlar shu yerdan oladi)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Telegram botni ishga tushiradi (long polling)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Faqat sozlamalarni tekshirib chiqadi, botni ishga tushirmaydi.",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Kelgan har bir xabarni va xatolarni ekranga chiqaradi.",
        )

    def handle(self, *args, **options):
        # Jurnal: --debug bilan hamma narsa ko'rinadi, aks holda faqat
        # ogohlantirish va xatolar.
        logging.basicConfig(
            level=logging.INFO if options["debug"] else logging.WARNING,
            format="%(asctime)s  %(levelname)-7s %(message)s",
            datefmt="%H:%M:%S",
        )

        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise CommandError(
                "TELEGRAM_BOT_TOKEN sozlanmagan.\n"
                "  1) Telegram'da @BotFather ga /newbot yozing\n"
                "  2) Bergan tokenini .env fayldagi TELEGRAM_BOT_TOKEN ga qo'ying"
            )

        # middleware_handler faqat shu bayroq bilan ishlaydi va u TeleBot
        # yaratilishidan OLDIN qo'yilishi shart - aks holda bot ishga
        # tushishda "Middleware is not enabled" xatosi bilan yiqiladi.
        telebot.apihelper.ENABLE_MIDDLEWARE = True
        telebot.apihelper.RETRY_ON_ERROR = True
        bot = telebot.TeleBot(token, parse_mode="HTML", use_class_middlewares=False)

        try:
            me = bot.get_me()
        except Exception as exc:
            raise CommandError(f"Telegram'ga ulanib bo'lmadi: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Bot ulandi: @{me.username}"))

        # Webhook va long polling birga ishlay olmaydi: agar botga qachondir
        # webhook qo'yilgan bo'lsa, getUpdates 409 Conflict qaytaradi va bot
        # hech qanday xabarni ko'rmaydi ("bot javob bermayapti"). Shuning
        # uchun qolgan webhook'ni o'zimiz olib tashlaymiz.
        try:
            hook = bot.get_webhook_info()
            if getattr(hook, "url", ""):
                self.stdout.write(
                    self.style.WARNING(f"Eski webhook topildi: {hook.url} - o'chirilmoqda")
                )
                bot.remove_webhook()
        except Exception as exc:  # webhook tekshiruvi majburiy emas
            logger.warning("Webhook holatini tekshirib bo'lmadi: %s", exc)

        if options["once"]:
            self.stdout.write("--once berilgani uchun to'xtatildi.")
            return

        register_handlers(bot)

        self.stdout.write(f"Sayt manzili: {settings.SITE_URL}")
        linked = TelegramLink.objects.filter(chat_id__isnull=False).count()
        self.stdout.write(f"Ulangan foydalanuvchilar: {linked}")
        if not linked:
            self.stdout.write(
                self.style.WARNING(
                    "Hali hech kim ulanmagan. Saytda: Sozlamalar -> Telegram bot -> Kod olish"
                )
            )
        self.stdout.write("\nKutilmoqda... (to'xtatish uchun Ctrl+C)")
        try:
            bot.infinity_polling(skip_pending=True, timeout=30)
        except KeyboardInterrupt:
            self.stdout.write("\nBot to'xtatildi.")
