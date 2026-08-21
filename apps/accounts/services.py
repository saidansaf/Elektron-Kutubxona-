"""Pul harakati: hisobni to'ldirish va balansdan pul yechish.

Nega alohida modul: bu amallarni ikki joydan chaqirish kerak — saytdan
(forma orqali) va Telegram botdan. Agar mantiq ikki nusxada yozilsa,
biri o'zgarganda ikkinchisi eskirib qoladi va pul hisobida farq paydo
bo'ladi. Shuning uchun qoidalar faqat shu yerda turadi.

Xuddi shu sabab bilan xarid mantiqi `apps/books/services.py` da.
"""

from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext as _

from .models import User, Withdrawal


class MoneyError(Exception):
    """Foydalanuvchiga ko'rsatiladigan tushunarli xato."""


def parse_amount(raw):
    """Matnni summaga aylantiradi.

    Botda foydalanuvchi "50 000" yoki "50000so'm" deb yozishi mumkin,
    shuning uchun raqam bo'lmagan belgilar tashlanadi.
    """
    text = "".join(ch for ch in str(raw) if ch.isdigit() or ch in ".,")
    text = text.replace(",", ".").strip(".")
    if not text:
        raise MoneyError(_("Summani raqam bilan yozing. Masalan: 50000"))
    try:
        amount = Decimal(text)
    except Exception as exc:
        raise MoneyError(_("Summani raqam bilan yozing. Masalan: 50000")) from exc
    if amount <= 0:
        raise MoneyError(_("Summa noldan katta bo'lishi kerak."))
    return amount.quantize(Decimal("0.01"))


def clean_card(raw):
    """Karta raqamini tekshiradi va faqat raqamlarini qaytaradi."""
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    if len(digits) < 16:
        raise MoneyError(_("Karta raqami 16 xonali bo'lishi kerak."))
    return digits[:16]


def request_withdrawal(seller, amount, card_number):
    """Pul yechish so'rovini yaratadi.

    Summa so'rov yuborilishi bilan balansdan ushlab qolinadi — aks holda
    bir pulni bir necha marta so'rash mumkin bo'lardi. Administrator rad
    etsa, pul qaytariladi (apps/core/admin_views.py).
    """
    amount = amount if isinstance(amount, Decimal) else parse_amount(amount)
    card = clean_card(card_number)

    if amount < settings.WITHDRAWAL_MIN:
        raise MoneyError(
            _("Eng kam summa %(min)s so'm.") % {"min": settings.WITHDRAWAL_MIN}
        )

    if seller.withdrawals.filter(status=Withdrawal.Status.PENDING).exists():
        raise MoneyError(_("Sizda ko'rib chiqilayotgan so'rov bor. Avval u hal bo'lsin."))

    with transaction.atomic():
        # Balansni bazadan qayta o'qiymiz: tekshiruvdan keyin xarid tushib,
        # mablag' kamaygan bo'lishi mumkin.
        fresh = User.objects.select_for_update().get(pk=seller.pk)
        if fresh.balance < amount:
            raise MoneyError(
                _("Balansingizda buncha mablag' yo'q. Mavjud: %(balance)s so'm.")
                % {"balance": int(fresh.balance)}
            )
        fresh.balance -= amount
        fresh.save(update_fields=["balance"])
        withdrawal = Withdrawal.objects.create(
            seller=fresh, amount=amount, card_number=card
        )

    seller.balance = fresh.balance
    return withdrawal
