"""To'lov sahifalari va provayder webhook'lari.

Ikki xil manzil bor va ular butunlay boshqacha:

* **Foydalanuvchi uchun** (`/tolov/holat/<id>/`, `/tolov/tarix/`) —
  oddiy sahifalar, kirish talab qilinadi.
* **Provayder uchun** (`/tolov/payme/`, `/tolov/click/`) — Payme va Click
  serverlari chaqiradi. Bu yerda sessiya ham, CSRF ham yo'q: himoya
  imzo va parol orqali (payme.check_auth / click.check_sign).
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.accounts.services import MoneyError

from . import click, payme, services, testmode
from .models import Payment, PaymentStatus

logger = logging.getLogger(__name__)


@login_required
def test_checkout_view(request, pk):
    """Test rejimidagi soxta to'lov sahifasi.

    Payme/Click sahifasining o'rnini bosadi. Jonli rejimda ochilmaydi —
    aks holda kitoblarni haqiqiy pul to'lamasdan olish mumkin bo'lardi.
    """
    if not testmode.is_test_mode():
        messages.error(request, _("Test rejimi o'chirilgan."))
        return redirect("books:catalog")

    payment = get_object_or_404(Payment, pk=pk, user=request.user)

    if request.method == "POST" and payment.is_open:
        try:
            if request.POST.get("action") == "pay":
                testmode.simulate_success(payment)
            else:
                testmode.simulate_cancel(payment)
        except MoneyError as exc:
            messages.error(request, str(exc))
        return redirect("payments:result", pk=payment.pk)

    return render(request, "payments/test_checkout.html", {"payment": payment})


@login_required
def result_view(request, pk):
    """To'lovdan keyingi sahifa: nima bo'lganini ko'rsatadi."""
    payment = get_object_or_404(Payment, pk=pk, user=request.user)
    return render(request, "payments/result.html", {"payment": payment})


# --- Provayder webhook'lari ---


@csrf_exempt
@require_POST
def payme_webhook(request):
    """Payme Merchant API kirish nuqtasi (JSON-RPC).

    Har doim 200 qaytaradi: JSON-RPC da xato javob tanasida beriladi,
    HTTP kodida emas. 500 qaytarilsa Payme so'rovni cheksiz takrorlaydi.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse(payme.error(payme.ERR_PARSE))

    response = payme.handle(payload, request.headers.get("Authorization", ""))
    return JsonResponse(response)


@csrf_exempt
@require_POST
def click_webhook(request):
    """Click SHOP-API kirish nuqtasi (oddiy forma so'rovi)."""
    return JsonResponse(click.handle(request.POST.dict()))


@login_required
def history_view(request):
    """Foydalanuvchining to'lovlar tarixi."""
    payments = Payment.objects.filter(user=request.user)[:50]
    return render(
        request,
        "payments/history.html",
        {"payments": payments, "statuses": PaymentStatus},
    )


def health_view(request):
    """Sozlamalar to'g'ri qo'yilganini tekshirish uchun (faqat xodimlar)."""
    if not request.user.is_staff:
        return HttpResponse(status=404)
    from django.conf import settings

    return JsonResponse(
        {
            "mode": settings.PAYMENT_MODE,
            "providers": [str(p) for p in services.available_providers()],
            "payme_ready": bool(settings.PAYME_MERCHANT_ID and settings.PAYME_KEY),
            "click_ready": bool(settings.CLICK_SERVICE_ID and settings.CLICK_SECRET_KEY),
        }
    )
