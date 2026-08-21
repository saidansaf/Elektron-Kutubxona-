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


def purchase_book(buyer, book, address=""):
    """Kitobni xaridorga biriktiradi va pulni sotuvchiga o'tkazadi.

    **Xaridorda hisob (balans) yo'q.** Har bir kitob karta orqali alohida
    to'lanadi, shuning uchun bu funksiya chaqirilganda pul allaqachon
    yechilgan bo'ladi — uni faqat to'lov tasdiqlangandan keyin chaqirish
    mumkin (`apps/payments/services.py`).

    Sotuvchining hisobi esa qoladi: bu uning daromadi, u yerdan pul
    yechish so'rovi beriladi.

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
        # `select_for_update`: bir sotuvchining ikkita kitobi bir vaqtda
        # sotilishi mumkin, daromad hisobi adashmasligi kerak.
        seller = User.objects.select_for_update().get(pk=book.seller_id)
        seller.balance += book.price
        seller.save(update_fields=["balance"])

        purchase = Purchase.objects.create(
            buyer=buyer,
            book=book,
            price_paid=book.price,
            address=address,
        )

    return purchase


def cancel_purchase(purchase):
    """Xaridni bekor qiladi va sotuvchining daromadini qaytaradi.

    To'lov qaytarilganda (Payme buni 12 soat ichida qila oladi) chaqiriladi.
    """
    with transaction.atomic():
        seller = User.objects.select_for_update().get(pk=purchase.book.seller_id)
        seller.balance -= purchase.price_paid
        seller.save(update_fields=["balance"])
        purchase.delete()
