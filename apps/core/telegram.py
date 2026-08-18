"""Telegram bilan ishlash: xabar yuborish va bildirishnomalar.

Bu modul botning "chiquvchi" tomoni - saytda biror voqea bo'lganda
foydalanuvchiga Telegram orqali xabar beradi. Botning "kiruvchi" tomoni
(buyruqlarga javob berish) `apps/core/management/commands/bot.py` da.

Muhim qoida: **bu yerdagi hech bir xato saytni to'xtatmasligi kerak**.
Telegram javob bermasa ham kitob sotib olinishi, xabar yuborilishi
kerak - shunchaki bildirishnoma bormaydi.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import override

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT = 10


def is_configured():
    return bool(getattr(settings, "TELEGRAM_BOT_TOKEN", ""))


def call(method, payload=None, timeout=TIMEOUT):
    """Telegram API'ga so'rov yuboradi.

    Xato bo'lsa `None` qaytaradi va jurnalga yozadi - chaqiruvchi tomon
    buni tekshirishi shart emas.
    """
    if not is_configured():
        return None

    url = API_BASE.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)
    data = json.dumps(payload or {}).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:200]
        logger.warning("Telegram %s xatosi %s: %s", method, exc.code, body)
    except Exception as exc:  # tarmoq uzilishi, timeout va boshqalar
        logger.warning("Telegram %s yuborilmadi: %s", method, exc)
    return None


def send_message(chat_id, text, keyboard=None, preview=False):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": not preview},
    }
    if keyboard is not None:
        payload["reply_markup"] = keyboard
    return call("sendMessage", payload)


def notify(user, text, keyboard=None):
    """Foydalanuvchiga xabar yuboradi (bot ulangan va yoqilgan bo'lsa).

    Xabar foydalanuvchi tanlagan tilda yuboriladi - u saytni ruscha
    ishlatsa, Telegram'da ham ruscha kelishi kerak.
    """
    link = getattr(user, "telegram", None)
    if link is None or not link.is_linked or not link.notifications:
        return None
    return send_message(link.chat_id, text, keyboard)


# --- Sayt voqealari ---


def notify_new_message(conversation, sender, text):
    """Suhbatda yangi xabar paydo bo'ldi."""
    recipient = conversation.other_side(sender)
    with override(getattr(recipient, "language", "uz")):
        body = _("💬 <b>%(sender)s</b> sizga yozdi\n<i>%(book)s</i>\n\n%(text)s") % {
            "sender": sender.username,
            "book": conversation.book.title,
            "text": text[:500],
        }
    notify(recipient, body)


def notify_sale(purchase):
    """Sotuvchiga kitobi sotilgani haqida xabar."""
    seller = purchase.book.seller
    with override(getattr(seller, "language", "uz")):
        body = _(
            "🎉 <b>Kitobingiz sotildi!</b>\n"
            "<i>%(book)s</i>\n"
            "Xaridor: %(buyer)s\n"
            "Summa: %(amount)s so'm"
        ) % {
            "book": purchase.book.title,
            "buyer": purchase.buyer.username,
            "amount": int(purchase.price_paid),
        }
    notify(seller, body)


def notify_withdrawal(withdrawal):
    """Sotuvchiga pul yechish so'rovi natijasi haqida xabar."""
    seller = withdrawal.seller
    with override(getattr(seller, "language", "uz")):
        if withdrawal.status == withdrawal.Status.APPROVED:
            body = _("✅ <b>To'lov amalga oshirildi</b>\n%(amount)s so'm → %(card)s") % {
                "amount": int(withdrawal.amount),
                "card": withdrawal.card_masked,
            }
        else:
            body = _("❌ <b>Pul yechish so'rovi rad etildi</b>\n%(amount)s so'm balansga qaytarildi.") % {
                "amount": int(withdrawal.amount),
            }
            if withdrawal.comment:
                body += f"\n<i>{withdrawal.comment}</i>"
    notify(seller, body)


def notify_admin_message(admin_message, recipients):
    """Administrator xabarini Telegram orqali ham yetkazadi."""
    for user in recipients:
        with override(getattr(user, "language", "uz")):
            title = admin_message.subject or _("Administratordan xabar")
            body = f"📢 <b>{title}</b>\n\n{admin_message.body[:800]}"
        notify(user, body)
