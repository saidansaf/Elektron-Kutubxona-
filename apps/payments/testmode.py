"""Test rejimi: provayderni o'rnini bosuvchi.

`PAYMENT_MODE=test` bo'lganda foydalanuvchi Payme yoki Click saytiga
emas, o'zimizdagi to'lov sahifasiga tushadi. "To'lash" bosilganda esa
shu modul **Payme/Click aynan yuboradigan so'rovlarni** yig'adi va
ularni haqiqiy protokol kodiga uzatadi.

Nega shunday, "shunchaki balansni oshirib qo'ya qolmadikmi"? Chunki u
holda protokol kodi hech qachon ishlamas edi va kalit kelgan kuni
xatolar birinchi marta jonli to'lovda chiqardi. Bu yerda esa
`CreateTransaction` → `PerformTransaction` zanjiri, imzo tekshiruvi,
summani solishtirish — hammasi haqiqiy yo'ldan o'tadi.

Farqi bitta: so'rovni Payme emas, o'zimiz yubordik.
"""

import base64
import time

from django.conf import settings
from django.utils.translation import gettext as _

from apps.accounts.services import MoneyError

from . import click, payme
from .models import Provider


def is_test_mode():
    return settings.PAYMENT_MODE != "live"


def simulate_success(payment):
    """To'lov muvaffaqiyatli o'tgan holatni o'ynaydi."""
    if payment.provider == Provider.PAYME:
        _payme_pay(payment)
    else:
        _click_pay(payment)
    payment.refresh_from_db()
    return payment


def simulate_cancel(payment):
    """Foydalanuvchi to'lovni bekor qilgan holatni o'ynaydi."""
    if payment.provider == Provider.PAYME:
        _payme_cancel(payment)
    else:
        _click_cancel(payment)
    payment.refresh_from_db()
    return payment


# --- Payme ---


def _payme_auth():
    return "Basic " + base64.b64encode(f"Paycom:{settings.PAYME_KEY}".encode()).decode()


def _payme_call(method, params):
    response = payme.handle(
        {"method": method, "params": params, "id": int(time.time())},
        auth_header=_payme_auth(),
    )
    if "error" in response:
        message = response["error"]["message"]
        raise MoneyError(
            _("To'lov amalga oshmadi: %(reason)s") % {"reason": message.get("uz", "xato")}
        )
    return response["result"]


def _payme_transaction_id(payment):
    """Payme tranzaksiyaga o'z ID sini beradi. Testda uni o'zimiz yasaymiz."""
    return f"test{payment.pk:08d}"


def _payme_params(payment):
    return {
        "amount": payment.amount_tiyin,
        "account": {settings.PAYME_ACCOUNT_FIELD: str(payment.pk)},
    }


def _payme_pay(payment):
    _payme_call("CheckPerformTransaction", _payme_params(payment))
    params = dict(_payme_params(payment))
    params.update({"id": _payme_transaction_id(payment), "time": int(time.time() * 1000)})
    _payme_call("CreateTransaction", params)
    _payme_call("PerformTransaction", {"id": _payme_transaction_id(payment)})


def _payme_cancel(payment):
    params = dict(_payme_params(payment))
    params.update({"id": _payme_transaction_id(payment), "time": int(time.time() * 1000)})
    _payme_call("CreateTransaction", params)
    _payme_call("CancelTransaction", {"id": _payme_transaction_id(payment), "reason": 1})


# --- Click ---


def _click_call(data, action):
    data = dict(data, action=action)
    data["sign_string"] = click.make_sign(data, action)
    response = click.handle(data)
    if response.get("error", 0) < 0:
        raise MoneyError(
            _("To'lov amalga oshmadi: %(reason)s") % {"reason": response.get("error_note", "")}
        )
    return response


def _click_base(payment):
    return {
        "click_trans_id": f"test{payment.pk}",
        "service_id": settings.CLICK_SERVICE_ID or "test",
        "click_paydoc_id": payment.pk,
        "merchant_trans_id": payment.pk,
        "amount": f"{payment.amount:.2f}",
        "error": 0,
        "error_note": "",
        "sign_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _click_pay(payment):
    prepared = _click_call(_click_base(payment), click.ACTION_PREPARE)
    data = dict(_click_base(payment), merchant_prepare_id=prepared["merchant_prepare_id"])
    _click_call(data, click.ACTION_COMPLETE)


def _click_cancel(payment):
    prepared = _click_call(_click_base(payment), click.ACTION_PREPARE)
    data = dict(
        _click_base(payment),
        merchant_prepare_id=prepared["merchant_prepare_id"],
        error=-9,
        error_note="Cancelled by user",
    )
    # Bekor qilinganda Click ham xato kodi bilan javob qaytaradi, shuning
    # uchun `_click_call` emas, to'g'ridan-to'g'ri chaqiramiz.
    data = dict(data, action=click.ACTION_COMPLETE)
    data["sign_string"] = click.make_sign(data, click.ACTION_COMPLETE)
    click.handle(data)
