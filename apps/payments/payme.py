"""Payme (Paycom) Merchant API.

Payme'da yo'nalish teskari: **Payme bizning saytimizni chaqiradi**. Biz
JSON-RPC serverimiz bo'lib, quyidagi oltita metodga javob beramiz:

| Metod | Payme nima so'ramoqda |
|---|---|
| `CheckPerformTransaction` | "Shu buyurtma bormi, summasi to'g'rimi?" |
| `CreateTransaction` | "Tranzaksiya ochdim, eslab qol" |
| `PerformTransaction` | "Pul yechildi, endi xizmatni ber" |
| `CancelTransaction` | "Bekor qilindi, orqaga qaytar" |
| `CheckTransaction` | "Holati qanaqa?" |
| `GetStatement` | "Falon oraliqdagi to'lovlarni ber (solishtiruv)" |

Protokol hujjati: https://developer.help.paycom.uz

Ikkita nozik joy:

1. **Summa tiyinda.** 50 000 so'm = 5 000 000 tiyin. Adashilsa, Payme
   summani noto'g'ri deb rad etadi.
2. **Har so'rov takrorlanishi mumkin.** Payme javobni olmasa, xuddi shu
   so'rovni yana yuboradi. Shuning uchun `PerformTransaction` ikkinchi
   marta kelganda balans qayta oshmasligi kerak — buni `services.mark_paid`
   ta'minlaydi.
"""

import base64
import hmac
import logging

from django.conf import settings
from django.utils import timezone

from .models import Payment, PaymentStatus, Provider
from . import services

logger = logging.getLogger(__name__)

# Payme tranzaksiya holatlari (protokolda shu raqamlar kutiladi)
STATE_CREATED = 1
STATE_PERFORMED = 2
STATE_CANCELLED = -1  # to'lanmasdan bekor qilingan
STATE_CANCELLED_AFTER = -2  # to'langandan keyin qaytarilgan

# Xato kodlari
ERR_PARSE = -32700
ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_AUTH = -32504
ERR_AMOUNT = -31001
ERR_TRANSACTION_NOT_FOUND = -31003
ERR_CANNOT_CANCEL = -31007
ERR_CANNOT_PERFORM = -31008
# -31050..-31099 oralig'i savdogarning o'z xatolari uchun ajratilgan
ERR_ORDER_NOT_FOUND = -31050

MESSAGES = {
    ERR_AUTH: {"uz": "Ruxsat yo'q", "ru": "Нет доступа", "en": "Not allowed"},
    ERR_METHOD_NOT_FOUND: {
        "uz": "Metod topilmadi",
        "ru": "Метод не найден",
        "en": "Method not found",
    },
    ERR_AMOUNT: {
        "uz": "Summa noto'g'ri",
        "ru": "Неверная сумма",
        "en": "Incorrect amount",
    },
    ERR_TRANSACTION_NOT_FOUND: {
        "uz": "Tranzaksiya topilmadi",
        "ru": "Транзакция не найдена",
        "en": "Transaction not found",
    },
    ERR_CANNOT_PERFORM: {
        "uz": "Amalni bajarib bo'lmaydi",
        "ru": "Невозможно выполнить операцию",
        "en": "Unable to perform operation",
    },
    ERR_CANNOT_CANCEL: {
        "uz": "Bekor qilib bo'lmaydi",
        "ru": "Невозможно отменить",
        "en": "Unable to cancel",
    },
    ERR_ORDER_NOT_FOUND: {
        "uz": "Buyurtma topilmadi",
        "ru": "Заказ не найден",
        "en": "Order not found",
    },
}


def check_auth(header):
    """`Authorization: Basic base64("Paycom:<kalit>")` ni tekshiradi.

    Busiz har kim bizning webhook'imizga "to'landi" deb yozib, balansini
    bepul to'ldirib olishi mumkin bo'lardi.
    """
    key = settings.PAYME_KEY
    if not key:
        return False
    if not header or not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:].strip()).decode("utf-8")
    except Exception:
        return False
    login, _, password = decoded.partition(":")
    # `compare_digest` — vaqt bo'yicha hujumdan himoya (kalitni belgima-belgi
    # taxmin qilishning oldini oladi).
    return login == "Paycom" and hmac.compare_digest(password, key)


def error(code, request_id=None, data=None):
    payload = {"code": code, "message": MESSAGES.get(code, MESSAGES[ERR_CANNOT_PERFORM])}
    if data is not None:
        payload["data"] = data
    return {"error": payload, "id": request_id}


def ok(result, request_id=None):
    return {"result": result, "id": request_id}


def handle(payload, auth_header=""):
    """Payme yuborgan JSON-RPC so'rovini bajaradi va javob lug'atini qaytaradi."""
    if not isinstance(payload, dict):
        return error(ERR_PARSE)

    request_id = payload.get("id")

    if not check_auth(auth_header):
        return error(ERR_AUTH, request_id)

    method = payload.get("method")
    params = payload.get("params") or {}
    if not isinstance(params, dict):
        return error(ERR_INVALID_REQUEST, request_id)

    handler = _METHODS.get(method)
    if handler is None:
        return error(ERR_METHOD_NOT_FOUND, request_id)

    try:
        return handler(params, request_id)
    except Exception:
        # Kutilmagan xato Payme uchun 500 emas, tushunarli xato bo'lishi
        # kerak — aks holda u so'rovni cheksiz takrorlaydi.
        logger.exception("Payme so'rovida kutilmagan xato: %s", method)
        return error(ERR_CANNOT_PERFORM, request_id)


# --- Metodlar ---


def _find_order(params):
    """`account.order_id` bo'yicha buyurtmani topadi."""
    account = params.get("account") or {}
    raw = account.get("order_id") or account.get(settings.PAYME_ACCOUNT_FIELD)
    try:
        return Payment.objects.get(pk=int(raw), provider=Provider.PAYME)
    except (TypeError, ValueError, Payment.DoesNotExist):
        return None


def _check_perform(params, request_id):
    payment = _find_order(params)
    if payment is None:
        return error(ERR_ORDER_NOT_FOUND, request_id, data="order_id")
    if int(params.get("amount") or 0) != payment.amount_tiyin:
        return error(ERR_AMOUNT, request_id)
    if payment.status == PaymentStatus.PAID:
        # Bir buyurtma ikki marta to'lanmasin.
        return error(ERR_CANNOT_PERFORM, request_id)
    return ok({"allow": True}, request_id)


def _create(params, request_id):
    transaction_id = params.get("id")

    # Payme shu tranzaksiyani ilgari ochgan bo'lishi mumkin (takroriy so'rov).
    existing = Payment.objects.filter(
        provider=Provider.PAYME, transaction_id=str(transaction_id)
    ).first()
    if existing:
        if existing.status != PaymentStatus.WAITING:
            return error(ERR_CANNOT_PERFORM, request_id)
        return ok(
            {
                "create_time": existing.created_time,
                "transaction": str(existing.pk),
                "state": STATE_CREATED,
            },
            request_id,
        )

    payment = _find_order(params)
    if payment is None:
        return error(ERR_ORDER_NOT_FOUND, request_id, data="order_id")
    if int(params.get("amount") or 0) != payment.amount_tiyin:
        return error(ERR_AMOUNT, request_id)
    if payment.status != PaymentStatus.CREATED:
        return error(ERR_CANNOT_PERFORM, request_id)

    services.mark_waiting(payment, transaction_id, int(params.get("time") or 0))
    return ok(
        {
            "create_time": payment.created_time,
            "transaction": str(payment.pk),
            "state": STATE_CREATED,
        },
        request_id,
    )


def _perform(params, request_id):
    payment = _by_transaction(params)
    if payment is None:
        return error(ERR_TRANSACTION_NOT_FOUND, request_id)

    if payment.status == PaymentStatus.PAID:
        # Takroriy so'rov: javob bir xil bo'lishi kerak, balans oshmaydi.
        return ok(
            {
                "transaction": str(payment.pk),
                "perform_time": payment.performed_time,
                "state": STATE_PERFORMED,
            },
            request_id,
        )

    if payment.status != PaymentStatus.WAITING:
        return error(ERR_CANNOT_PERFORM, request_id)

    payment = services.mark_paid(payment, _now_ms())
    return ok(
        {
            "transaction": str(payment.pk),
            "perform_time": payment.performed_time,
            "state": STATE_PERFORMED,
        },
        request_id,
    )


def _cancel(params, request_id):
    payment = _by_transaction(params)
    if payment is None:
        return error(ERR_TRANSACTION_NOT_FOUND, request_id)

    was_paid = payment.status == PaymentStatus.PAID
    if payment.status != PaymentStatus.CANCELLED:
        payment = services.mark_cancelled(payment, params.get("reason"), _now_ms())
    else:
        was_paid = payment.performed_time > 0

    return ok(
        {
            "transaction": str(payment.pk),
            "cancel_time": payment.cancelled_time,
            "state": STATE_CANCELLED_AFTER if was_paid else STATE_CANCELLED,
        },
        request_id,
    )


def _check(params, request_id):
    payment = _by_transaction(params)
    if payment is None:
        return error(ERR_TRANSACTION_NOT_FOUND, request_id)
    return ok(_state_payload(payment), request_id)


def _statement(params, request_id):
    """Payme kunlik solishtiruv uchun so'raydi (vaqt millisekundlarda)."""
    start = int(params.get("from") or 0)
    end = int(params.get("to") or 0)
    rows = Payment.objects.filter(
        provider=Provider.PAYME,
        created_time__gte=start,
        created_time__lte=end,
    ).exclude(transaction_id="")

    transactions = []
    for payment in rows:
        row = _state_payload(payment)
        row.update(
            {
                "id": payment.transaction_id,
                "time": payment.created_time,
                "amount": payment.amount_tiyin,
                "account": {settings.PAYME_ACCOUNT_FIELD: str(payment.pk)},
            }
        )
        transactions.append(row)
    return ok({"transactions": transactions}, request_id)


_METHODS = {
    "CheckPerformTransaction": _check_perform,
    "CreateTransaction": _create,
    "PerformTransaction": _perform,
    "CancelTransaction": _cancel,
    "CheckTransaction": _check,
    "GetStatement": _statement,
}


# --- Yordamchilar ---


def _by_transaction(params):
    return Payment.objects.filter(
        provider=Provider.PAYME, transaction_id=str(params.get("id"))
    ).first()


def _state_payload(payment):
    if payment.status == PaymentStatus.PAID:
        state = STATE_PERFORMED
    elif payment.status == PaymentStatus.CANCELLED:
        state = STATE_CANCELLED_AFTER if payment.performed_time else STATE_CANCELLED
    else:
        state = STATE_CREATED
    return {
        "create_time": payment.created_time,
        "perform_time": payment.performed_time,
        "cancel_time": payment.cancelled_time,
        "transaction": str(payment.pk),
        "state": state,
        "reason": payment.cancel_reason,
    }


def _now_ms():
    return int(timezone.now().timestamp() * 1000)


def checkout_url(payment, return_url=""):
    """Foydalanuvchi yo'naltiriladigan Payme sahifasi manzili.

    Parametrlar `m=...;ac.order_id=...;a=...` ko'rinishida yig'ilib,
    base64 ga o'raladi — Payme shunday talab qiladi.
    """
    parts = [
        f"m={settings.PAYME_MERCHANT_ID}",
        f"ac.{settings.PAYME_ACCOUNT_FIELD}={payment.pk}",
        f"a={payment.amount_tiyin}",
    ]
    if return_url:
        parts.append(f"c={return_url}")
    encoded = base64.b64encode(";".join(parts).encode()).decode()
    return f"{settings.PAYME_CHECKOUT_URL}/{encoded}"
