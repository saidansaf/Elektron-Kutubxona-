"""AI yordamchi sahifasi va yordamchi so'rovlar."""

import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from . import ai
from .cache import rate_limit, rate_limit_state

HISTORY_KEY = "ai_history"
MAX_HISTORY = 12


def _limit_exceeded_response():
    """Chegara tugaganda beriladigan javob.

    Bepul API kalitlarining kunlik limiti bor: chegara bo'lmasa bitta
    foydalanuvchi uni bir o'zi tugatib, qolganlarga AI ishlamay qoladi.
    """
    minutes = max(1, settings.AI_RATE_LIMIT_WINDOW // 60)
    return JsonResponse(
        {
            "error": _(
                "So'rovlar chegarasiga yetdingiz. %(minutes)s daqiqadan keyin qayta urinib ko'ring."
            )
            % {"minutes": minutes}
        },
        status=429,
    )


@login_required
def assistant_view(request):
    return render(
        request,
        "core/ai_assistant.html",
        {
            "history": request.session.get(HISTORY_KEY, []),
            "ai_ready": ai.is_configured(),
            "ai_messages_left": rate_limit_state(
                "ai-chat", request.user.pk, settings.AI_RATE_LIMIT_MESSAGES
            ),
            "ai_messages_limit": settings.AI_RATE_LIMIT_MESSAGES,
        },
    )


@login_required
@require_POST
def assistant_send_view(request):
    """Foydalanuvchi xabarini AI ga yuboradi va javobni qaytaradi."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": _("So'rovni o'qib bo'lmadi.")}, status=400)

    text = (payload.get("message") or "").strip()
    if not text:
        return JsonResponse({"error": _("Xabar bo'sh.")}, status=400)

    allowed, left = rate_limit(
        "ai-chat",
        request.user.pk,
        settings.AI_RATE_LIMIT_MESSAGES,
        settings.AI_RATE_LIMIT_WINDOW,
    )
    if not allowed:
        return _limit_exceeded_response()

    history = request.session.get(HISTORY_KEY, [])
    history.append({"role": "user", "content": text})

    try:
        answer = ai.chat(history[-MAX_HISTORY:])
    except ai.AIError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    history.append({"role": "assistant", "content": answer})
    request.session[HISTORY_KEY] = history[-MAX_HISTORY:]
    request.session.modified = True
    return JsonResponse({"answer": answer, "left": left})


@login_required
@require_POST
def assistant_clear_view(request):
    request.session[HISTORY_KEY] = []
    request.session.modified = True
    return JsonResponse({"ok": True})


@login_required
@require_POST
def describe_book_view(request):
    """Kitob qo'shish formasida tavsifni AI yozib beradi."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": _("So'rovni o'qib bo'lmadi.")}, status=400)

    title = (payload.get("title") or "").strip()
    if not title:
        return JsonResponse({"error": _("Avval kitob nomini kiriting.")}, status=400)

    allowed, _left = rate_limit(
        "ai-chat",
        request.user.pk,
        settings.AI_RATE_LIMIT_MESSAGES,
        settings.AI_RATE_LIMIT_WINDOW,
    )
    if not allowed:
        return _limit_exceeded_response()

    try:
        text = ai.describe_book(
            title,
            author=(payload.get("author") or "").strip(),
            genre=(payload.get("genre") or "").strip(),
            language=(payload.get("language") or "uz").strip(),
        )
    except ai.AIError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    return JsonResponse({"description": text})
