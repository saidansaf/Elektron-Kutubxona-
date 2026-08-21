"""To'lov buyurtmasi ustidagi amallar.

Bu modul provayderlarni bilmaydi — Payme ham, Click ham shu yerdagi
funksiyalarni chaqiradi. Sabab: pul harakati bitta joyda bo'lishi kerak,
aks holda ikkita provayder ikki xil qoida bilan ishlab qoladi.

Eng muhim talab — **idempotentlik**. Provayder bir xil so'rovni bir necha
marta yuborishi mumkin (tarmoq uzilsa, javob yetib bormasa). Shuning
uchun `mark_paid` ikkinchi marta chaqirilsa balansni yana oshirmaydi.
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.accounts.services import MoneyError, parse_amount

from .models import Payment, PaymentStatus, Provider

logger = logging.getLogger(__name__)


def available_providers():
    """Sozlangan to'lov tizimlari ro'yxati.

    Test rejimida ikkalasi ham ochiq: kalit kerak emas. Jonli rejimda
    faqat kaliti to'ldirilganlari ko'rinadi — aks holda foydalanuvchi
    ishlamaydigan tugmani bosadi.
    """
    if settings.PAYMENT_MODE != "live":
        return [Provider.PAYME, Provider.CLICK]

    ready = []
    if settings.PAYME_MERCHANT_ID and settings.PAYME_KEY:
        ready.append(Provider.PAYME)
    if settings.CLICK_SERVICE_ID and settings.CLICK_MERCHANT_ID and settings.CLICK_SECRET_KEY:
        ready.append(Provider.CLICK)
    return ready


def create_payment(user, book, provider):
    """Kitob uchun yangi to'lov buyurtmasini yaratadi.

    Xaridorda hisob yo'q: har bir kitob alohida to'lanadi. Shuning uchun
    summa har doim kitob narxiga teng va uni foydalanuvchi tanlamaydi.

    Bu yerda hech qanday pul harakati bo'lmaydi — faqat "shu kitobni
    to'lamoqchi" degan yozuv qoladi. Kitob `mark_paid` da beriladi.
    """
    amount = book.price if isinstance(book.price, Decimal) else parse_amount(book.price)

    if amount <= 0:
        raise MoneyError(_("To'lov summasi noto'g'ri."))
    if amount > settings.PAYMENT_MAX:
        raise MoneyError(_("Eng ko'p summa %(max)s so'm.") % {"max": settings.PAYMENT_MAX})

    if provider not in available_providers():
        raise MoneyError(_("Bu to'lov tizimi hozircha sozlanmagan."))

    return Payment.objects.create(user=user, amount=amount, provider=provider, book=book)


def mark_paid(payment, transaction_time=0):
    """To'lovni yakunlaydi va kitobni xaridorga beradi.

    Takroriy chaqiruvda hech narsa qilmaydi va bor `Payment` ni qaytaradi
    — provayder javobni olmasa xuddi shu so'rovni qayta yuboradi.
    """
    with transaction.atomic():
        fresh = Payment.objects.select_for_update().get(pk=payment.pk)

        if fresh.status == PaymentStatus.PAID:
            return fresh  # allaqachon hisoblangan
        if fresh.status == PaymentStatus.CANCELLED:
            raise MoneyError(_("Bekor qilingan to'lovni yakunlab bo'lmaydi."))

        fresh.status = PaymentStatus.PAID
        fresh.performed_time = transaction_time or _now_ms()
        fresh.save(update_fields=["status", "performed_time", "updated_at"])

    _finish_book_purchase(fresh)

    payment.status = fresh.status
    payment.performed_time = fresh.performed_time
    return fresh


def _finish_book_purchase(payment):
    """To'lovdan keyin kitobni xaridorga biriktiradi.

    Alohida tranzaksiyada: xarid o'tmasa ham to'lov "to'landi" bo'lib
    qolishi kerak, chunki pul haqiqatan yechilgan.

    Xato yutilmaydi, jurnalga yoziladi — aks holda "pul ketdi, kitob
    yo'q" holati sezilmay qolardi. Bunday holat faqat poyga vaziyatida
    bo'lishi mumkin (kitob shu orada boshqa yo'l bilan olingan yoki
    sotuvdan yechilgan) va uni administrator qo'lda hal qiladi.
    """
    if not payment.book_id or payment.purchase_id:
        return

    from apps.books.services import PurchaseError, purchase_book

    try:
        purchase = purchase_book(payment.user, payment.book, address=payment.address)
    except PurchaseError as exc:
        logger.warning(
            "To'lov #%s: kitob berilmadi (%s). Administrator ko'rib chiqishi kerak.",
            payment.pk,
            exc,
        )
        return

    payment.purchase = purchase
    payment.save(update_fields=["purchase", "updated_at"])

    from apps.core import telegram

    telegram.notify_sale(purchase)


def mark_cancelled(payment, reason=None, transaction_time=0):
    """To'lovni bekor qiladi.

    To'langan bo'lsa xarid ham bekor qilinadi: kitob xaridordan olinadi
    va sotuvchining daromadi qaytariladi. Payme buni "reverse" deb ataydi
    va uni 12 soat ichida qila oladi.
    """
    from apps.books.services import cancel_purchase

    with transaction.atomic():
        fresh = Payment.objects.select_for_update().get(pk=payment.pk)

        if fresh.status == PaymentStatus.CANCELLED:
            return fresh

        if fresh.status == PaymentStatus.PAID and fresh.purchase_id:
            cancel_purchase(fresh.purchase)
            fresh.purchase = None

        fresh.status = PaymentStatus.CANCELLED
        fresh.cancel_reason = reason
        fresh.cancelled_time = transaction_time or _now_ms()
        fresh.save(
            update_fields=["purchase", "status", "cancel_reason", "cancelled_time", "updated_at"]
        )

    payment.status = fresh.status
    return fresh


def mark_waiting(payment, transaction_id, transaction_time=0):
    """Provayder tranzaksiyani ochdi."""
    payment.status = PaymentStatus.WAITING
    payment.transaction_id = str(transaction_id)[:64]
    payment.created_time = transaction_time or _now_ms()
    payment.save(update_fields=["status", "transaction_id", "created_time", "updated_at"])
    return payment


def checkout_link(payment, base_url=""):
    """Foydalanuvchi to'lash uchun ochadigan manzil.

    `base_url` — saytning ildizi ("https://kutubxona.uz"). Saytdan
    chaqirilganda so'rovdan olinadi, botdan chaqirilganda `SITE_URL` dan.

    Test rejimida o'zimizdagi sinov sahifasi qaytadi, jonli rejimda esa
    provayderning haqiqiy to'lov sahifasi.
    """
    from django.urls import reverse

    from . import click, payme
    from .testmode import is_test_mode

    site = (base_url or settings.SITE_URL or "").rstrip("/")

    if is_test_mode():
        return f"{site}{reverse('payments:test_checkout', args=[payment.pk])}"

    result_url = f"{site}{reverse('payments:result', args=[payment.pk])}"
    if payment.provider == Provider.PAYME:
        return payme.checkout_url(payment, result_url)
    return click.checkout_url(payment, result_url)


def _now_ms():
    from django.utils import timezone

    return int(timezone.now().timestamp() * 1000)
