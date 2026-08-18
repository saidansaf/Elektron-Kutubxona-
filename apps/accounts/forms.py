from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import Role, Theme, User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label=_("Email"))

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label=_("Foydalanuvchi nomi"))
    password = forms.CharField(label=_("Parol"), widget=forms.PasswordInput)

    def confirm_login_allowed(self, user):
        # Bloklangan foydalanuvchiga sababni ko'rsatamiz (is_active=False bo'lgani
        # uchun standart xabar tushunarsiz bo'lardi).
        if getattr(user, "is_blocked", False):
            reason = user.blocked_reason or _("Sabab ko'rsatilmagan.")
            raise forms.ValidationError(
                _("Hisobingiz bloklangan. %(reason)s") % {"reason": reason},
                code="blocked",
            )
        super().confirm_login_allowed(user)


class AdminLoginForm(AuthenticationForm):
    """Maxfiy admin kirish sahifasi uchun - faqat superuser/staff kirishi mumkin."""

    username = forms.CharField(label=_("Admin login"))
    password = forms.CharField(label=_("Admin parol"), widget=forms.PasswordInput)

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not (user.is_staff or user.is_superuser):
            raise forms.ValidationError(_("Bu sahifaga faqat administrator kira oladi."), code="not_admin")


class RoleSelectForm(forms.Form):
    role = forms.ChoiceField(
        choices=[
            (Role.SELLER, _("Sotuvchiman - kitob sotmoqchiman")),
            (Role.BUYER, _("Sotib oluvchiman - kitob o'qimoqchiman")),
        ],
        widget=forms.RadioSelect,
        label=_("Kim bo'lib kirmoqchisiz?"),
    )


class SettingsForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=[(Role.SELLER, _("Sotuvchi")), (Role.BUYER, _("Sotib oluvchi"))],
        widget=forms.RadioSelect,
        label=_("Rejim"),
    )

    class Meta:
        model = User
        fields = ("role", "theme", "language", "phone", "bio", "avatar")
        widgets = {
            "theme": forms.RadioSelect,
            "language": forms.RadioSelect,
            "bio": forms.Textarea(attrs={"rows": 3, "placeholder": _("Bir-ikki og'iz o'zingiz haqingizda")}),
            "phone": forms.TextInput(attrs={"placeholder": "+998 90 123 45 67"}),
        }


class TopUpForm(forms.Form):
    """Hisobni to'ldirish.

    Diqqat: o'quv loyihasi - haqiqiy to'lov amalga oshirilmaydi, karta raqami
    saqlanmaydi. Faqat format tekshiriladi va chek uchun oxirgi 4 raqam olinadi.
    """

    amount = forms.DecimalField(
        label=_("Summa (so'm)"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "50000", "inputmode": "numeric"}),
    )
    card_number = forms.CharField(
        label=_("Karta raqami"),
        widget=forms.TextInput(attrs={"placeholder": "8600 1234 5678 9012", "inputmode": "numeric"}),
    )
    card_expiry = forms.CharField(
        label=_("Amal qilish muddati"),
        widget=forms.TextInput(attrs={"placeholder": "MM/YY"}),
    )

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        low, high = settings.TOPUP_MIN, settings.TOPUP_MAX
        if amount < low:
            raise forms.ValidationError(
                _("Eng kam summa %(min)s so'm.") % {"min": low}
            )
        if amount > high:
            raise forms.ValidationError(
                _("Eng ko'p summa %(max)s so'm.") % {"max": high}
            )
        return amount

    def clean_card_number(self):
        raw = (self.cleaned_data.get("card_number") or "").replace(" ", "").replace("-", "")
        if not raw.isdigit() or not 12 <= len(raw) <= 19:
            raise forms.ValidationError(_("Karta raqami 12-19 ta raqamdan iborat bo'lishi kerak."))
        return raw


class WithdrawalForm(forms.Form):
    """Sotuvchining balansdan pul yechish so'rovi.

    Mavjud balansdan ko'p so'ray olmaydi va bir vaqtda faqat bitta so'rov
    ko'rib chiqilishi mumkin.
    """

    amount = forms.DecimalField(
        label=_("Summa (so'm)"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "100000", "inputmode": "numeric"}),
    )
    card_number = forms.CharField(
        label=_("Karta raqami"),
        help_text=_("Pul shu kartaga o'tkaziladi."),
        widget=forms.TextInput(attrs={"placeholder": "8600 1234 5678 9012", "inputmode": "numeric"}),
    )

    def __init__(self, *args, seller=None, **kwargs):
        self.seller = seller
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount < settings.WITHDRAWAL_MIN:
            raise forms.ValidationError(
                _("Eng kam summa %(min)s so'm.") % {"min": settings.WITHDRAWAL_MIN}
            )
        if self.seller is not None and amount > self.seller.balance:
            raise forms.ValidationError(
                _("Balansingizda buncha mablag' yo'q. Mavjud: %(balance)s so'm.")
                % {"balance": self.seller.balance}
            )
        return amount

    def clean_card_number(self):
        raw = (self.cleaned_data.get("card_number") or "").replace(" ", "").replace("-", "")
        if not raw.isdigit() or not 12 <= len(raw) <= 19:
            raise forms.ValidationError(_("Karta raqami 12-19 ta raqamdan iborat bo'lishi kerak."))
        return raw
