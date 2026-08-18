"""Botning webhook rejimi.

Ikki xil ishlash usuli bor:

**Long polling** (`python manage.py bot`) — bot Telegramdan "yangilik
bormi?" deb doim so'rab turadi. Alohida, to'xtamaydigan jarayon kerak.
Lokal ishlab chiqish uchun qulay.

**Webhook** (shu modul) — aksincha, Telegram yangilikni saytga o'zi
yuboradi. Alohida jarayon kerak emas: bot saytning ichida, oddiy sahifa
kabi ishlaydi.

Render, Vercel va shunga o'xshash bepul xizmatlarda ikkinchisi yagona
yo'l — u yerda "doim ishlab turadigan ikkinchi jarayon" bepul tarifda
berilmaydi.

Xavfsizlik: manzilda maxfiy so'z bor va Telegram yuboradigan
`X-Telegram-Bot-Api-Secret-Token` sarlavhasi tekshiriladi. Ikkalasi ham
mos kelmasa so'rov 404 bilan rad etiladi — begona odam botga soxta
xabar yubora olmaydi.
"""

import hashlib
import hmac
import json
import logging
import threading

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

SECRET_HEADER = "HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN"

# Bot obyekti bir marta yaratiladi va barcha so'rovlar uchun qayta
# ishlatiladi: handlerlarni har so'rovda qaytadan ro'yxatdan o'tkazish
# ortiqcha ish bo'lardi.
_bot = None
_lock = threading.Lock()


def webhook_secret():
    """Manzildagi maxfiy so'z.

    Tokendan hosil qilinadi, shuning uchun alohida sozlash shart emas va
    tokenning o'zi manzilda ochiq turmaydi.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        return ""
    return hashlib.sha256(f"kutubxona-webhook:{token}".encode()).hexdigest()[:32]


def get_bot():
    """Handlerlar ulangan bot obyekti (birinchi murojaatda yaratiladi)."""
    global _bot
    if _bot is not None:
        return _bot
    with _lock:
        if _bot is not None:  # boshqa ip ulgurgan bo'lishi mumkin
            return _bot
        import telebot

        from .handlers import register_handlers

        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            return None

        telebot.apihelper.ENABLE_MIDDLEWARE = True
        bot = telebot.TeleBot(token, parse_mode="HTML", use_class_middlewares=False, threaded=False)
        register_handlers(bot)
        _bot = bot
        return _bot


@csrf_exempt
@require_POST
def telegram_webhook(request, secret):
    """Telegram yuborgan yangilikni qabul qiladi.

    Javob har doim tez qaytishi kerak: Telegram javobni kutadi va kech
    qolsa xuddi shu yangilikni qayta-qayta yuboraveradi. Shuning uchun
    xato chiqsa ham 200 qaytariladi (xato jurnalga yoziladi) — aks holda
    bitta buzuq xabar cheksiz aylanib qolardi.
    """
    expected = webhook_secret()
    if not expected:
        return HttpResponseNotFound()

    # Ikki bosqichli tekshiruv: manzildagi so'z va Telegram sarlavhasi.
    header = request.META.get(SECRET_HEADER, "")
    if not hmac.compare_digest(secret, expected) or not hmac.compare_digest(header, expected):
        logger.warning("Webhook: noto'g'ri maxfiy so'z, so'rov rad etildi")
        return HttpResponseNotFound()

    bot = get_bot()
    if bot is None:
        return HttpResponseNotFound()

    try:
        import telebot

        payload = json.loads(request.body.decode("utf-8"))
        update = telebot.types.Update.de_json(payload)
        bot.process_new_updates([update])
    except Exception:
        logger.exception("Webhook yangiligini qayta ishlashda xato")

    return HttpResponse("ok")
