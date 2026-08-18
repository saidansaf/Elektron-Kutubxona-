"""Sayt va bot uchun umumiy amallar.

Xarid mantiqi ikki joydan chaqiriladi: saytdagi to'lov sahifasidan va
Telegram botdan. Uni ikki marta yozib qo'yish xavfli - biri o'zgarganda
ikkinchisi eskirib qoladi va pul hisobida farq paydo bo'ladi. Shuning
uchun mantiq shu yerda, bitta joyda turadi.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .models import Purchase

User = get_user_model()


class PurchaseError(Exception):
    """Xaridni amalga oshirib bo'lmadi. Matni foydalanuvchiga ko'rsatiladi."""


def purchase_book(buyer, book, card_last4="", address=""):
    """Kitobni sotib oladi va pulni sotuvchiga o'tkazadi.

    Balans bazadan qayta o'qiladi (`select_for_update`): foydalanuvchi ayni
    paytda saytda ham, botda ham xarid qilayotgan bo'lishi mumkin, eskirgan
    qiymatga ishonib bo'lmaydi.

    Muvaffaqiyatli bo'lsa `Purchase` qaytaradi, aks holda `PurchaseError`
    ko'taradi.
    """
    if not book.is_active:
        raise PurchaseError(_("Bu kitob sotuvda emas."))

    if Purchase.objects.filter(buyer=buyer, book=book).exists():
        raise PurchaseError(_("Siz bu kitobni allaqachon sotib olgansiz."))

    if book.seller_id == buyer.pk:
        raise PurchaseError(_("O'z kitobingizni sotib ololmaysiz."))

    with transaction.atomic():
        fresh_buyer = User.objects.select_for_update().get(pk=buyer.pk)
        if fresh_buyer.balance < book.price:
            raise PurchaseError(_("Hisobingizda mablag' yetarli emas."))

        seller = User.objects.select_for_update().get(pk=book.seller_id)

        fresh_buyer.balance -= book.price
        fresh_buyer.save(update_fields=["balance"])
        seller.balance += book.price
        seller.save(update_fields=["balance"])

        purchase = Purchase.objects.create(
            buyer=fresh_buyer,
            book=book,
            price_paid=book.price,
            card_last4=card_last4,
            address=address,
        )

    # Chaqiruvchi tomondagi obyekt eskirmasligi uchun
    buyer.balance = fresh_buyer.balance
    return purchase
