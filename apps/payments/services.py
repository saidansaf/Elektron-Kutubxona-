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

from apps.accounts.models import TopUp, User
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


def create_payment(user, amount, provider, book=None, address=""):
    """Yangi to'lov buyurtmasini yaratadi.

    Balans bu yerda oshmaydi — faqat "shuncha to'lamoqchi" degan yozuv
    qoladi. Balans `mark_paid` da oshadi.

    `book` berilsa, to'lov aynan shu kitob uchun: tasdiqlangach kitob
    o'zi sotib olinadi.
    """
    amount = amount if isinstance(amount, Decimal) else parse_amount(amount)

    high = settings.TOPUP_MAX
    if amount > high:
        raise MoneyError(_("Eng ko'p summa %(max)s so'm.") % {"max": high})

    if book is None:
        # Eng kam summa faqat "shunchaki to'ldirish" uchun. Kitob to'lovida
        # summa kitob narxidan kelib chiqadi va u chegaradan kichik bo'lishi
        # mumkin — o'shanda ham to'lashga ruxsat berish kerak.
        if amount < settings.TOPUP_MIN:
            raise MoneyError(_("Eng kam summa %(min)s so'm.") % {"min": settings.TOPUP_MIN})
    elif amount <= 0:
        raise MoneyError(_("To'lov summasi noto'g'ri."))

    if provider not in available_providers():
        raise MoneyError(_("Bu to'lov tizimi hozircha sozlanmagan."))

    return Payment.objects.create(
        user=user, amount=amount, provider=provider, book=book, address=address
    )


def amount_for_book(user, book):
    """Kitobni olish uchun yana qancha to'lash kerakligi.

    Balansda pul bo'lsa, faqat yetmagan qismi to'lanadi.
    """
    missing = book.price - user.balance
    return missing if missing > 0 else Decimal("0.00")


def mark_paid(payment, transaction_time=0):
    """To'lovni yakunlaydi va balansni oshiradi.

    Takroriy chaqiruvda hech narsa qilmaydi va bor `Payment` ni qaytaradi.
    """
    with transaction.atomic():
        fresh = Payment.objects.select_for_update().get(pk=payment.pk)

        if fresh.status == PaymentStatus.PAID:
            return fresh  # allaqachon hisoblangan, ikkinchi marta oshirmaymiz
        if fresh.status == PaymentStatus.CANCELLED:
            raise MoneyError(_("Bekor qilingan to'lovni yakunlab bo'lmaydi."))

        user = User.objects.select_for_update().get(pk=fresh.user_id)
        user.balance += fresh.amount
        user.save(update_fields=["balance"])

        fresh.topup = TopUp.objects.create(user=user, amount=fresh.amount)
        fresh.status = PaymentStatus.PAID
        fresh.performed_time = transaction_time or _now_ms()
        fresh.save(update_fields=["topup", "status", "performed_time", "updated_at"])

    _finish_book_purchase(fresh)

    payment.status = fresh.status
    payment.performed_time = fresh.performed_time
    return fresh


def _finish_book_purchase(payment):
    """Kitob uchun qilingan to'lovdan keyin xaridni yakunlaydi.

    Alohida tranzaksiyada: xarid o'tmasa ham to'lov "to'landi" bo'lib
    qolishi kerak, chunki pul haqiqatan yechilgan. Bunday holatda pul
    balansda turaveradi va foydalanuvchi kitobni qo'lda sotib oladi.

    Xato yutilmaydi, jurnalga yoziladi — aks holda "pul ketdi, kitob
    yo'q" holati sezilmay qolardi.
    """
    if not payment.book_id or payment.purchase_id:
        return

    from apps.books.services import PurchaseError, purchase_book

    try:
        purchase = purchase_book(payment.user, payment.book, address=payment.address)
    except PurchaseError as exc:
        logger.warning(
            "To'lov #%s: kitob sotib olinmadi (%s). Pul balansda qoldi.", payment.pk, exc
        )
        return

    payment.purchase = purchase
    payment.save(update_fields=["purchase", "updated_at"])

    from apps.core import telegram

    telegram.notify_sale(purchase)


def mark_cancelled(payment, reason=None, transaction_time=0):
    """To'lovni bekor qiladi.

    To'langan bo'lsa pul balansdan qaytariladi. Payme buni "reverse"
    deb ataydi va uni 12 soat ichida qila oladi.

    Balans yetmay qolgan bo'lsa (foydalanuvchi pulni sarflab ulgurgan)
    balans manfiy bo'ladi. Bu ataylab: pulni "yo'q qilib" yuborgandan
    ko'ra qarzni ko'rsatib turgan ma'qul, aks holda hisob-kitob buziladi.
    """
    with transaction.atomic():
        fresh = Payment.objects.select_for_update().get(pk=payment.pk)

        if fresh.status == PaymentStatus.CANCELLED:
            return fresh

        if fresh.status == PaymentStatus.PAID:
            user = User.objects.select_for_update().get(pk=fresh.user_id)
            user.balance -= fresh.amount
            user.save(update_fields=["balance"])
            if fresh.topup_id:
                fresh.topup.delete()
                fresh.topup = None

        fresh.status = PaymentStatus.CANCELLED
        fresh.cancel_reason = reason
        fresh.cancelled_time = transaction_time or _now_ms()
        fresh.save(
            update_fields=["topup", "status", "cancel_reason", "cancelled_time", "updated_at"]
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
