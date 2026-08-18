"""Sayt ichidagi administrator boshqaruv sahifalari.

Django'ning standart admin paneliga qo'shimcha - foydalanuvchilarni bloklash,
o'chirish, ularga xabar yuborish va hammaga e'lon tarqatish uchun.
"""

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.accounts.models import AdminMessage, Withdrawal
from apps.core import telegram
from apps.books.models import Purchase, Review

User = get_user_model()


class MessageForm(forms.Form):
    subject = forms.CharField(required=False, label=_("Sarlavha"), max_length=150)
    body = forms.CharField(label=_("Xabar matni"), widget=forms.Textarea(attrs={"rows": 4}))


class BlockForm(forms.Form):
    reason = forms.CharField(required=False, label=_("Sabab"), max_length=255)


class ResetPasswordForm(forms.Form):
    """Administrator foydalanuvchiga yangi parol belgilaydi.

    Mavjud parolni ko'rsatib bo'lmaydi - u qaytarib bo'lmaydigan tarzda
    shifrlangan (hash). Shuning uchun yagona yo'l - yangisini o'rnatish.
    """

    new_password = forms.CharField(
        label=_("Yangi parol"),
        min_length=8,
        widget=forms.TextInput(attrs={"placeholder": _("Kamida 8 belgi")}),
    )


@staff_member_required
def user_list_view(request):
    q = request.GET.get("q", "").strip()
    users = User.objects.annotate(
        books_total=Count("books", distinct=True),
        purchases_total=Count("purchases", distinct=True),
    ).order_by("-date_joined")
    if q:
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q))

    page_obj = Paginator(users, 25).get_page(request.GET.get("page"))
    return render(request, "core/admin_users.html", {"page_obj": page_obj, "q": q})


@staff_member_required
def user_detail_view(request, pk):
    user_obj = get_object_or_404(
        User.objects.annotate(
            books_total=Count("books", distinct=True),
            purchases_total=Count("purchases", distinct=True),
        ),
        pk=pk,
    )
    return render(
        request,
        "core/admin_user_detail.html",
        {
            "user_obj": user_obj,
            "message_form": MessageForm(),
            "block_form": BlockForm(initial={"reason": user_obj.blocked_reason}),
            "password_form": ResetPasswordForm(),
            "purchases": Purchase.objects.filter(buyer=user_obj).select_related("book")[:10],
            "reviews": Review.objects.filter(buyer=user_obj).select_related("book")[:10],
            "sent_messages": AdminMessage.objects.filter(recipient=user_obj)[:10],
        },
    )


@staff_member_required
@require_POST
def user_block_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj.is_superuser:
        messages.error(request, _("Administratorni bloklab bo'lmaydi."))
        return redirect("core:admin_user_detail", pk=pk)

    form = BlockForm(request.POST)
    reason = form.cleaned_data["reason"] if form.is_valid() else ""

    user_obj.is_blocked = not user_obj.is_blocked
    user_obj.blocked_reason = reason if user_obj.is_blocked else ""
    # is_active ga tegmaymiz: uni False qilsak Django parolni ham tekshirmay,
    # "login yoki parol xato" deb umumiy xabar berardi va bloklash sababi
    # foydalanuvchiga ko'rinmasdi. Blok LoginForm va middleware orqali ushlanadi.
    user_obj.save(update_fields=["is_blocked", "blocked_reason"])

    if user_obj.is_blocked:
        messages.success(request, _("Foydalanuvchi bloklandi."))
    else:
        messages.success(request, _("Blok olib tashlandi."))
    return redirect("core:admin_user_detail", pk=pk)


@staff_member_required
@require_POST
def user_delete_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj.is_superuser:
        messages.error(request, _("Administratorni o'chirib bo'lmaydi."))
        return redirect("core:admin_user_detail", pk=pk)
    if user_obj == request.user:
        messages.error(request, _("O'zingizni o'chira olmaysiz."))
        return redirect("core:admin_user_detail", pk=pk)

    username = user_obj.username
    user_obj.delete()
    messages.success(request, _("'%(name)s' foydalanuvchisi o'chirildi.") % {"name": username})
    return redirect("core:admin_users")


@staff_member_required
@require_POST
def user_message_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    form = MessageForm(request.POST)
    if form.is_valid():
        admin_message = AdminMessage.objects.create(
            recipient=user_obj,
            sender=request.user,
            subject=form.cleaned_data["subject"],
            body=form.cleaned_data["body"],
        )
        telegram.notify_admin_message(admin_message, [user_obj])
        messages.success(request, _("Xabar yuborildi. Foydalanuvchi saytga kirganda ko'radi."))
    else:
        messages.error(request, _("Xabar matni bo'sh bo'lmasligi kerak."))
    return redirect("core:admin_user_detail", pk=pk)


@staff_member_required
@require_POST
def user_reset_password_view(request, pk):
    """Foydalanuvchiga yangi parol belgilaydi.

    Eski parolni ko'rsatish imkonsiz: Django uni PBKDF2 bilan bir tomonlama
    shifrlab saqlaydi va uni qaytarib ochib bo'lmaydi.
    """
    user_obj = get_object_or_404(User, pk=pk)
    form = ResetPasswordForm(request.POST)
    if form.is_valid():
        new_password = form.cleaned_data["new_password"]
        user_obj.set_password(new_password)
        user_obj.save(update_fields=["password"])
        messages.success(
            request,
            _("'%(name)s' uchun yangi parol o'rnatildi: %(pwd)s")
            % {"name": user_obj.username, "pwd": new_password},
        )
    else:
        messages.error(request, _("Parol kamida 8 belgidan iborat bo'lishi kerak."))
    return redirect("core:admin_user_detail", pk=pk)


@staff_member_required
def broadcast_view(request):
    """Barcha foydalanuvchilarga e'lon yuborish."""
    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            admin_message = AdminMessage.objects.create(
                recipient=None,
                sender=request.user,
                subject=form.cleaned_data["subject"],
                body=form.cleaned_data["body"],
                is_broadcast=True,
            )
            # Telegram ulagan foydalanuvchilarga darhol yetkazamiz.
            telegram.notify_admin_message(
                admin_message,
                User.objects.filter(telegram__chat_id__isnull=False, telegram__notifications=True),
            )
            messages.success(request, _("E'lon barcha foydalanuvchilarga yuborildi."))
            return redirect("core:admin_dashboard")
    else:
        form = MessageForm()

    return render(
        request,
        "core/admin_broadcast.html",
        {"form": form, "sent": AdminMessage.objects.filter(is_broadcast=True)[:10]},
    )


@staff_member_required
def withdrawal_list_view(request):
    """Sotuvchilarning pul yechish so'rovlari."""
    pending = Withdrawal.objects.filter(status=Withdrawal.Status.PENDING).select_related("seller")
    processed = (
        Withdrawal.objects.exclude(status=Withdrawal.Status.PENDING)
        .select_related("seller")[:30]
    )
    return render(
        request,
        "core/admin_withdrawals.html",
        {"pending": pending, "processed": processed},
    )


@staff_member_required
@require_POST
def withdrawal_decide_view(request, pk):
    """So'rovni tasdiqlash yoki rad etish.

    Summa so'rov yuborilganda balansdan yechib qo'yilgan edi, shuning uchun
    tasdiqlashda balansga tegilmaydi. Rad etilganda pul qaytariladi.
    """
    withdrawal = get_object_or_404(Withdrawal, pk=pk)
    if not withdrawal.is_pending:
        messages.info(request, _("Bu so'rov allaqachon ko'rib chiqilgan."))
        return redirect("core:admin_withdrawals")

    decision = request.POST.get("decision")
    comment = (request.POST.get("comment") or "").strip()[:255]

    with transaction.atomic():
        locked = Withdrawal.objects.select_for_update().get(pk=withdrawal.pk)
        if not locked.is_pending:
            return redirect("core:admin_withdrawals")

        if decision == "approve":
            locked.status = Withdrawal.Status.APPROVED
            messages.success(
                request,
                _("%(amount)s so'm to'landi deb belgilandi.") % {"amount": locked.amount},
            )
        else:
            locked.status = Withdrawal.Status.REJECTED
            seller = User.objects.select_for_update().get(pk=locked.seller_id)
            seller.balance += locked.amount
            seller.save(update_fields=["balance"])
            messages.info(
                request,
                _("So'rov rad etildi, %(amount)s so'm balansga qaytarildi.")
                % {"amount": locked.amount},
            )

        locked.comment = comment
        locked.processed_at = timezone.now()
        locked.save(update_fields=["status", "comment", "processed_at"])

    telegram.notify_withdrawal(locked)
    return redirect("core:admin_withdrawals")
