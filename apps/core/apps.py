import logging
import threading

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        _auto_set_webhook()


def _auto_set_webhook():
    """Server ko'tarilganda Telegram webhook'ini o'zi yoqadi.

    Nega kerak: Render'ning bepul tarifida "Shell" tugmasi yo'q, ya'ni
    serverda qo'lda buyruq yozib bo'lmaydi. Webhook esa yoqilmasa bot
    umuman javob bermaydi. Shuning uchun uni server o'zi yoqadi.

    Faqat AUTO_SET_WEBHOOK=1 bo'lganda ishlaydi — lokal ishlashda va
    testlarda tegmaydi (u yerda `manage.py bot` polling rejimi ishlatiladi).

    Ish alohida ipda bajariladi: Telegram javob bermay qolsa ham sayt
    kutib turmasin. Xato chiqsa faqat jurnalga yoziladi — bot ishlamasligi
    saytni to'xtatib qo'yishi mumkin emas.
    """
    from django.conf import settings

    if not getattr(settings, "AUTO_SET_WEBHOOK", False):
        return
    if not getattr(settings, "TELEGRAM_BOT_TOKEN", ""):
        return

    site = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    if not site.startswith("https://"):
        logger.warning("Webhook yoqilmadi: SITE_URL HTTPS emas (%s)", site or "bo'sh")
        return

    def worker():
        try:
            from apps.core import telegram
            from apps.core.botlib.webhook import webhook_secret

            secret = webhook_secret()
            url = f"{site}/tg/{secret}/"

            # Allaqachon o'sha manzilga qo'yilgan bo'lsa qayta so'rov yubormaymiz:
            # har ishga tushishda Telegram'ni bezovta qilishning hojati yo'q.
            current = (telegram.call("getWebhookInfo") or {}).get("result", {}).get("url", "")
            if current == url:
                logger.info("Webhook allaqachon o'rnatilgan: %s", url)
                return

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
                logger.warning("Telegram webhook o'rnatildi: %s", url)
            else:
                logger.error("Webhook o'rnatilmadi: %s", response)
        except Exception:
            logger.exception("Webhook o'rnatishda kutilmagan xato")

    threading.Thread(target=worker, name="set-webhook", daemon=True).start()
