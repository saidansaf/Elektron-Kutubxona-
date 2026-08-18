from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    NONE = "none", _("Tanlanmagan")
    SELLER = "seller", _("Sotuvchi")
    BUYER = "buyer", _("Sotib oluvchi")


class Theme(models.TextChoices):
    LIGHT = "light", _("Yorug'")
    DARK = "dark", _("Qorong'i")


class User(AbstractUser):
    role = models.CharField(_("Rol"), max_length=10, choices=Role.choices, default=Role.NONE)
    theme = models.CharField(_("Mavzu"), max_length=5, choices=Theme.choices, default=Theme.LIGHT)
    language = models.CharField(
        _("Til"),
        max_length=5,
        choices=settings.LANGUAGES if hasattr(settings, "LANGUAGES") else [],
        default="uz",
    )
    phone = models.CharField(_("Telefon raqami"), max_length=20, blank=True)
    avatar = models.ImageField(_("Profil rasmi"), upload_to="avatars/", blank=True, null=True)
    balance = models.DecimalField(_("Hisob balansi"), max_digits=12, decimal_places=2, default=Decimal("0.00"))
    bio = models.TextField(_("O'zingiz haqingizda"), blank=True)
    is_blocked = models.BooleanField(_("Bloklangan"), default=False)
    blocked_reason = models.CharField(_("Bloklash sababi"), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Foydalanuvchi")
        verbose_name_plural = _("Foydalanuvchilar")

    @property
    def is_seller(self):
        return self.role == Role.SELLER

    @property
    def is_buyer(self):
        return self.role == Role.BUYER

    @property
    def role_chosen(self):
        return self.role != Role.NONE

    @property
    def initials(self):
        """Avatar bo'lmaganda ko'rsatiladigan bosh harf."""
        source = (self.first_name or self.username or "?").strip()
        return source[0].upper() if source else "?"

    def __str__(self):
        return self.username


class AdminMessage(models.Model):
    """Administrator yuborgan xabar.

    `recipient` bo'sh bo'lsa - bu hammaga yuborilgan e'lon (broadcast).
    Foydalanuvchi saytga kirganda o'qilmagan xabarlari ko'rsatiladi.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_messages",
        null=True,
        blank=True,
        verbose_name=_("Qabul qiluvchi"),
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_admin_messages",
        verbose_name=_("Yuboruvchi"),
    )
    subject = models.CharField(_("Sarlavha"), max_length=150, blank=True)
    body = models.TextField(_("Xabar matni"))
    is_broadcast = models.BooleanField(_("Hammaga"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Administrator xabari")
        verbose_name_plural = _("Administrator xabarlari")

    def __str__(self):
        return self.subject or self.body[:40]


class TopUp(models.Model):
    """Hisobni to'ldirish yozuvi.

    Eslatma: haqiqiy to'lov tizimi ulanmagan - bu o'quv loyihasi. Karta
    ma'lumotlari saqlanmaydi, faqat chek uchun oxirgi 4 raqam qoladi.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="topups")
    amount = models.DecimalField(_("Summa"), max_digits=12, decimal_places=2)
    card_last4 = models.CharField(_("Karta oxirgi 4 raqami"), max_length=4, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Hisob to'ldirish")
        verbose_name_plural = _("Hisob to'ldirishlar")

    def __str__(self):
        return f"{self.user} +{self.amount}"


class TelegramLink(models.Model):
    """Saytdagi hisobni Telegram akkaunti bilan bog'laydi.

    Bog'lash bir martalik kod orqali: foydalanuvchi saytda kod oladi va
    uni botga yuboradi. Shu sababli botga parol kiritish shart emas.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="telegram"
    )
    chat_id = models.BigIntegerField(_("Telegram chat ID"), unique=True, null=True, blank=True)
    username = models.CharField(_("Telegram username"), max_length=64, blank=True)
    code = models.CharField(_("Ulash kodi"), max_length=8, blank=True)
    code_created_at = models.DateTimeField(null=True, blank=True)
    notifications = models.BooleanField(_("Bildirishnomalar"), default=True)
    linked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Telegram ulanishi")
        verbose_name_plural = _("Telegram ulanishlari")

    def __str__(self):
        return f"{self.user} ↔ {self.chat_id or self.code}"

    @property
    def is_linked(self):
        return self.chat_id is not None

    def code_is_fresh(self, minutes=15):
        """Kod hali amal qiladimi.

        Kod muddatsiz bo'lsa, uni bir marta ko'rgan odam istalgan vaqtda
        ishlatib, hisobni egallab olishi mumkin edi.
        """
        if not self.code or not self.code_created_at:
            return False
        return timezone.now() - self.code_created_at < timedelta(minutes=minutes)


class Withdrawal(models.Model):
    """Sotuvchining balansdan pul yechish so'rovi.

    So'rov yuborilganda summa balansdan darhol ushlab qolinadi (bir pulni
    ikki marta so'ramaslik uchun). Administrator rad etsa, pul qaytariladi.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Ko'rib chiqilmoqda")
        APPROVED = "approved", _("To'landi")
        REJECTED = "rejected", _("Rad etildi")

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="withdrawals"
    )
    amount = models.DecimalField(_("Summa"), max_digits=12, decimal_places=2)
    card_number = models.CharField(_("Karta raqami"), max_length=25)
    status = models.CharField(_("Holati"), max_length=10, choices=Status.choices, default=Status.PENDING)
    comment = models.CharField(_("Administrator izohi"), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(_("Ko'rib chiqilgan vaqti"), null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Pul yechish so'rovi")
        verbose_name_plural = _("Pul yechish so'rovlari")

    def __str__(self):
        return f"{self.seller} -{self.amount} ({self.status})"

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def card_masked(self):
        digits = "".join(ch for ch in self.card_number if ch.isdigit())
        return f"**** {digits[-4:]}" if len(digits) >= 4 else self.card_number


class MessageRead(models.Model):
    """Foydalanuvchi qaysi xabarni o'qiganini belgilaydi."""

    message = models.ForeignKey(AdminMessage, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="message_reads")
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("message", "user")
