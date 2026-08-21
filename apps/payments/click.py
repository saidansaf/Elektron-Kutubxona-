"""Click SHOP-API.

Click ham Payme kabi **bizni chaqiradi**, lekin JSON-RPC emas, oddiy
forma so'rovi bilan va faqat ikkita bosqichda:

| Bosqich | `action` | Click nima so'ramoqda |
|---|---|---|
| `Prepare` | `0` | "Shu buyurtma bormi? Summasi to'g'rimi? Tayyorlan" |
| `Complete` | `1` | "Pul yechildi (yoki xato bo'ldi), yakunla" |

Hujjat: https://docs.click.uz

Xavfsizlik imzo orqali: har so'rovda `sign_string` keladi va u maxfiy
kalit bilan hisoblangan MD5 bo'lishi kerak. Imzo mos kelmasa so'rov rad
etiladi — busiz istalgan odam "to'landi" deb yozib yuborishi mumkin edi.

Nozik joy: `Complete` bosqichida Click **xato bilan ham** kelishi mumkin
(`error < 0` — masalan foydalanuvchi bekor qildi). U holda buyurtmani
bekor qilamiz, balansni oshirmaymiz.
"""

import hashlib
import hmac
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings

from .models import Payment, PaymentStatus, Provider
from . import services

logger = logging.getLogger(__name__)

ACTION_PREPARE = 0
ACTION_COMPLETE = 1

# Click hujjatidagi xato kodlari
OK = 0
ERR_SIGN = -1
ERR_AMOUNT = -2
ERR_ACTION = -3
ERR_ALREADY_PAID = -4
ERR_USER_NOT_FOUND = -5
ERR_TRANSACTION_NOT_FOUND = -6
ERR_BAD_REQUEST = -8
ERR_CANCELLED = -9

NOTES = {
    OK: "Success",
    ERR_SIGN: "SIGN CHECK FAILED",
    ERR_AMOUNT: "Incorrect parameter amount",
    ERR_ACTION: "Action not found",
    ERR_ALREADY_PAID: "Already paid",
    ERR_USER_NOT_FOUND: "User does not exist",
    ERR_TRANSACTION_NOT_FOUND: "Transaction does not exist",
    ERR_BAD_REQUEST: "Error in request from click",
    ERR_CANCELLED: "Transaction cancelled",
}


def make_sign(data, action):
    """Click kutadigan MD5 imzoni hisoblaydi.

    Tartib qat'iy — hujjatdagidan bir belgi ham chetga chiqmasligi kerak,
    aks holda imzo mos kelmaydi.
    """
    parts = [
        str(data.get("click_trans_id", "")),
        str(data.get("service_id", "")),
        settings.CLICK_SECRET_KEY,
        str(data.get("merchant_trans_id", "")),
    ]
    if action == ACTION_COMPLETE:
        parts.append(str(data.get("merchant_prepare_id", "")))
    parts += [
        str(data.get("amount", "")),
        str(action),
        str(data.get("sign_time", "")),
    ]
    return hashlib.md5("".join(parts).encode()).hexdigest()


def check_sign(data, action):
    expected = make_sign(data, action)
    return hmac.compare_digest(expected, str(data.get("sign_string", "")))


def handle(data):
    """Click yuborgan so'rovni bajaradi va javob lug'atini qaytaradi."""
    try:
        action = int(data.get("action"))
    except (TypeError, ValueError):
        return _reply(data, ERR_ACTION)

    if action == ACTION_PREPARE:
        handler = _prepare
    elif action == ACTION_COMPLETE:
        handler = _complete
    else:
        return _reply(data, ERR_ACTION)

    if not settings.CLICK_SECRET_KEY or not check_sign(data, action):
        return _reply(data, ERR_SIGN)

    try:
        return handler(data)
    except Exception:
        logger.exception("Click so'rovida kutilmagan xato (action=%s)", action)
        return _reply(data, ERR_BAD_REQUEST)


def _prepare(data):
    payment = _find_payment(data)
    if payment is None:
        return _reply(data, ERR_TRANSACTION_NOT_FOUND)
    if payment.status == PaymentStatus.PAID:
        return _reply(data, ERR_ALREADY_PAID)
    if payment.status == PaymentStatus.CANCELLED:
        return _reply(data, ERR_CANCELLED)
    if not _amount_matches(data, payment):
        return _reply(data, ERR_AMOUNT)

    services.mark_waiting(payment, data.get("click_trans_id", ""))
    return _reply(data, OK, merchant_prepare_id=payment.pk)


def _complete(data):
    payment = _find_payment(data)
    if payment is None:
        return _reply(data, ERR_TRANSACTION_NOT_FOUND)
    if not _amount_matches(data, payment):
        return _reply(data, ERR_AMOUNT)

    # Click o'z tomonidagi xatoni shu maydonda yetkazadi (masalan
    # foydalanuvchi to'lovni bekor qildi). Bunda balans oshmaydi.
    try:
        click_error = int(data.get("error") or 0)
    except (TypeError, ValueError):
        click_error = 0
    if click_error < 0:
        if payment.is_open:
            services.mark_cancelled(payment, click_error)
        return _reply(data, ERR_CANCELLED)

    if payment.status == PaymentStatus.CANCELLED:
        return _reply(data, ERR_CANCELLED)
    if payment.status == PaymentStatus.PAID:
        # Takroriy so'rov: balans qayta oshmaydi, javob esa muvaffaqiyatli.
        return _reply(data, OK, merchant_confirm_id=payment.pk)

    services.mark_paid(payment)
    return _reply(data, OK, merchant_confirm_id=payment.pk)


def _find_payment(data):
    try:
        pk = int(data.get("merchant_trans_id"))
    except (TypeError, ValueError):
        return None
    return Payment.objects.filter(pk=pk, provider=Provider.CLICK).first()


def _amount_matches(data, payment):
    """Summani solishtiradi.

    Click summani "50000.00" ko'rinishidagi matn qilib yuboradi, shuning
    uchun `Decimal` orqali solishtiriladi (float'da yaxlitlash xatosi
    bo'lishi mumkin).
    """
    try:
        amount = Decimal(str(data.get("amount")))
    except (InvalidOperation, TypeError):
        return False
    return amount.quantize(Decimal("0.01")) == payment.amount.quantize(Decimal("0.01"))


def _reply(data, code, **extra):
    reply = {
        "click_trans_id": data.get("click_trans_id", ""),
        "merchant_trans_id": data.get("merchant_trans_id", ""),
        "error": code,
        "error_note": NOTES.get(code, "Error"),
    }
    reply.update(extra)
    return reply


def checkout_url(payment, return_url=""):
    """Foydalanuvchi yo'naltiriladigan Click to'lov sahifasi."""
    from urllib.parse import urlencode

    params = {
        "service_id": settings.CLICK_SERVICE_ID,
        "merchant_id": settings.CLICK_MERCHANT_ID,
        "amount": f"{payment.amount:.2f}",
        "transaction_param": payment.pk,
    }
    if return_url:
        params["return_url"] = return_url
    return f"{settings.CLICK_CHECKOUT_URL}?{urlencode(params)}"
