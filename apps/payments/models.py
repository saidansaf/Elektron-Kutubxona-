"""To'lov buyurtmasi.

Nega alohida model kerak: haqiqiy to'lov bir zumda tugamaydi. Foydalanuvchi
tugmani bosgandan keyin Payme yoki Click sahifasiga o'tadi, kartasini
kiritadi, SMS kodni tasdiqlaydi — bu bir necha daqiqa davom etishi mumkin.
Shu vaqt ichida saytda "kutilayotgan buyurtma" turishi kerak, aks holda
provayder "shu buyurtmani to'ladim" deb qaytganda uni topa olmaymiz.

Muhim qoida: **kitob faqat provayder tasdiqlaganda beriladi.** Foydalanuvchi
to'lov sahifasiga o'tgani hech narsani anglatmaydi — u yerdan qaytmasligi
ham mumkin.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Provider(models.TextChoices):
    PAYME = "payme", "Payme"
    CLICK = "click", "Click"


class PaymentStatus(models.TextChoices):
    # Buyurtma yaratildi, foydalanuvchi hali to'lov sahifasiga o'tmadi
    # yoki o'tdi-yu, provayder hali bizga murojaat qilmadi.
    CREATED = "created", _("Yaratildi")
    # Provayder tranzaksiyani ochdi va pulni "ushlab turibdi".
    WAITING = "waiting", _("Kutilmoqda")
    # Pul o'tdi va kitob xaridorga berildi.
    PAID = "paid", _("To'landi")
    # Bekor qilindi. To'langandan keyin ham bekor qilinishi mumkin
    # (Payme buni 12 soat ichida qila oladi) — u holda kitob qaytariladi.
    CANCELLED = "cancelled", _("Bekor qilindi")


class Payment(models.Model):
    """Bitta to'lov urinishi."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    provider = models.CharField(_("To'lov tizimi"), max_length=10, choices=Provider.choices)
    amount = models.DecimalField(_("Summa"), max_digits=12, decimal_places=2)
    status = models.CharField(
        _("Holati"), max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.CREATED
    )

    # Provayder tomonidagi identifikator: Payme'da `_id`, Click'da
    # `click_trans_id`. Takroriy so'rovni tanish uchun kerak.
    transaction_id = models.CharField(_("Tranzaksiya ID"), max_length=64, blank=True, db_index=True)

    # Payme tranzaksiya vaqtini millisekundlarda beradi va `CheckTransaction`
    # da aynan o'shani qaytarishimizni talab qiladi.
    created_time = models.BigIntegerField(default=0)
    performed_time = models.BigIntegerField(default=0)
    cancelled_time = models.BigIntegerField(default=0)
    cancel_reason = models.IntegerField(null=True, blank=True)

    # Har bir to'lov aynan bitta kitob uchun: xaridorda hisob (balans)
    # yo'q, kitoblar bittalab karta orqali to'lanadi.
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        verbose_name=_("Kitob"),
    )
    # Xarid uchun kerak bo'ladigan manzil. To'lov sahifasiga o'tishdan oldin
    # yozib qo'yiladi, chunki provayderdan qaytgach forma qayta
    # to'ldirilmaydi.
    address = models.CharField(_("Uy manzili"), max_length=255, blank=True)
    purchase = models.OneToOneField(
        "books.Purchase",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("To'lov")
        verbose_name_plural = _("To'lovlar")
        indexes = [models.Index(fields=["provider", "transaction_id"])]

    def __str__(self):
        return f"#{self.pk} {self.get_provider_display()} {self.amount} ({self.status})"

    @property
    def amount_tiyin(self):
        """Payme summani tiyinda kutadi (1 so'm = 100 tiyin)."""
        return int(self.amount * 100)

    @property
    def is_open(self):
        """Hali hal bo'lmagan buyurtma."""
        return self.status in (PaymentStatus.CREATED, PaymentStatus.WAITING)

    @classmethod
    def from_tiyin(cls, value):
        return (Decimal(value) / 100).quantize(Decimal("0.01"))
