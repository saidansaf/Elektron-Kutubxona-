import secrets

from django.conf import settings
from django.conf import settings as dj_settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _

from apps.core.decorators import seller_required
from apps.core.middleware import THEME_SESSION_KEY

from . import services

from .forms import (
    AdminLoginForm,
    LoginForm,
    RegisterForm,
    RoleSelectForm,
    SettingsForm,
    WithdrawalForm,
)
from .models import Role, TelegramLink, User, Withdrawal


# Katalog va kitob sahifasi hammaga ochiq. Ro'yxatdan o'tish faqat sotib
# olmoqchi bo'lganda so'raladi — o'shanda foydalanuvchi qayerdan kelganini
# yo'qotmaslik kerak. Manzil sessiyada saqlanadi, chunki oradan rol tanlash
# qadami o'tadi.
NEXT_SESSION_KEY = "after_auth_next"


def _safe_next(request, url):
    """Faqat shu saytning ichki manzillariga ruxsat (ochiq redirect emas)."""
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return None


def _remember_next(request):
    target = _safe_next(request, request.POST.get("next") or request.GET.get("next"))
    if target:
        request.session[NEXT_SESSION_KEY] = target
    return target


def _pop_next(request, default="core:home"):
    target = _safe_next(request, request.session.pop(NEXT_SESSION_KEY, ""))
    return redirect(target) if target else redirect(default)


def register_view(request):
    if request.user.is_authenticated:
        return redirect("core:home")

    next_url = _remember_next(request)

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, _("Ro'yxatdan muvaffaqiyatli o'tdingiz!"))
            return redirect("accounts:role_select")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form, "next": next_url})


class LoginPageView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm

    def dispatch(self, request, *args, **kwargs):
        _remember_next(request)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        user = self.request.user
        if not user.role_chosen and not (user.is_staff or user.is_superuser):
            return reverse("accounts:role_select")
        target = _safe_next(self.request, self.request.session.pop(NEXT_SESSION_KEY, ""))
        return target or reverse("core:home")


def logout_view(request):
    auth_logout(request)
    messages.info(request, _("Tizimdan chiqdingiz."))
    return redirect("core:home")


@login_required
def role_select_view(request):
    if request.user.role_chosen:
        return redirect("core:home")
    if request.method == "POST":
        form = RoleSelectForm(request.POST)
        if form.is_valid():
            request.user.role = form.cleaned_data["role"]
            request.user.save()
            messages.success(request, _("Rolingiz saqlandi!"))
            # Foydalanuvchi kitob sotib olmoqchi bo'lib kelgan bo'lsa,
            # o'sha kitobga qaytariladi.
            return _pop_next(request)
    else:
        form = RoleSelectForm()
    return render(request, "accounts/role_select.html", {"form": form})


@login_required
def settings_view(request):
    if request.method == "POST":
        form = SettingsForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()
            request.session[THEME_SESSION_KEY] = user.theme
            response = redirect("accounts:settings")
            response.set_cookie(dj_settings.LANGUAGE_COOKIE_NAME, user.language)
            messages.success(request, _("Sozlamalar saqlandi."))
            return response
    else:
        form = SettingsForm(instance=request.user)
    return render(request, "accounts/settings.html", {"form": form})


class AdminLoginView(LoginView):
    """`#admin` orqali ochiladigan maxfiy administrator kirish sahifasi."""

    template_name = "accounts/admin_login.html"
    authentication_form = AdminLoginForm

    def get_success_url(self):
        return reverse("core:admin_dashboard")


@seller_required
def withdrawal_view(request):
    """Sotuvchining pul yechish so'rovi.

    Summa so'rov yuborilishi bilan daromaddan ushlab qolinadi - aks holda
    bir pulni bir necha marta so'rash mumkin bo'lardi. Administrator rad
    etsa, pul avtomatik qaytariladi.
    """
    seller = request.user
    pending = seller.withdrawals.filter(status=Withdrawal.Status.PENDING).first()

    if request.method == "POST" and not pending:
        form = WithdrawalForm(request.POST, seller=seller)
        if form.is_valid():
            # Pul harakati sayt va bot uchun bitta joyda (services.py)
            try:
                services.request_withdrawal(
                    seller, form.cleaned_data["amount"], form.cleaned_data["card_number"]
                )
            except services.MoneyError as exc:
                messages.error(request, str(exc))
                return redirect("accounts:withdrawal")
            messages.success(
                request,
                _("So'rov yuborildi. Administrator tasdiqlagach, pul kartangizga o'tkaziladi."),
            )
            return redirect("accounts:withdrawal")
    else:
        form = WithdrawalForm(seller=seller)

    return render(
        request,
        "accounts/withdrawal.html",
        {
            "form": form,
            "pending": pending,
            "history": seller.withdrawals.all()[:10],
            "min_amount": settings.WITHDRAWAL_MIN,
        },
    )


@login_required
def telegram_link_view(request):
    """Telegram botni hisobga ulash uchun bir martalik kod beradi."""
    link, _created = TelegramLink.objects.get_or_create(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "unlink":
            link.chat_id = None
            link.code = ""
            link.linked_at = None
            link.save()
            messages.info(request, _("Telegram uzildi."))
        elif action == "notifications":
            link.notifications = not link.notifications
            link.save(update_fields=["notifications"])
        else:
            # Yangi kod: eskisi ishlamay qoladi
            link.code = f"{secrets.randbelow(1000000):06d}"
            link.code_created_at = timezone.now()
            link.save(update_fields=["code", "code_created_at"])
        return redirect("accounts:telegram")

    return render(
        request,
        "accounts/telegram.html",
        {
            "link": link,
            "bot_username": settings.TELEGRAM_BOT_USERNAME,
            "bot_configured": bool(settings.TELEGRAM_BOT_TOKEN),
        },
    )


class PasswordResetRequestView(auth_views.PasswordResetView):
    """Parolni tiklash so'rovi.

    SMTP sozlangan bo'lsa xat yuboriladi. Sozlanmagan bo'lsa xat konsolga
    chiqadi - bunday holda DEBUG rejimida havolani ekranda ham ko'rsatamiz,
    aks holda loyihani lokal sinab ko'rib bo'lmasdi.
    """

    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.pop("password_reset_link", None)

        # Faqat DEBUG va SMTP sozlanmagan holatda: havolani ekranda ko'rsatamiz.
        if settings.DEBUG and not settings.EMAIL_CONFIGURED:
            email = form.cleaned_data["email"]
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                self.request.session["password_reset_link"] = self.request.build_absolute_uri(
                    reverse("accounts:password_reset_confirm", kwargs={"uidb64": uid, "token": token})
                )
        return response


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dev_link"] = self.request.session.pop("password_reset_link", None)
        context["email_configured"] = settings.EMAIL_CONFIGURED
        return context


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
