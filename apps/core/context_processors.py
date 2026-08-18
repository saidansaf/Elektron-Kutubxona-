from django.conf import settings
from django.db.models import Q

from .cache import content_version


def site_preferences(request):
    return {
        "current_theme": getattr(request, "theme", "light"),
        "supported_languages": settings.LANGUAGES,
        "book_languages": settings.BOOK_LANGUAGES,
        "admin_telegram": settings.ADMIN_TELEGRAM_URL,
        # Keshlangan shablon fragmentlari shu raqamga bog'lanadi: kitob
        # yoki sharh o'zgarsa raqam oshadi va eski nusxa ishlatilmaydi.
        "cache_version": content_version(),
    }


def admin_messages(request):
    """Foydalanuvchining o'qilmagan administrator xabarlari.

    Shaxsiy xabarlar va hammaga yuborilgan e'lonlar birga qaytariladi.
    """
    if not request.user.is_authenticated:
        return {"unread_admin_messages": [], "unread_messages": 0}

    from apps.accounts.models import AdminMessage

    # union() ishlatilmaydi: SQLite compound so'rov ichida ORDER BY ni qabul qilmaydi.
    read_ids = request.user.message_reads.values_list("message_id", flat=True)
    unread = (
        AdminMessage.objects.filter(Q(recipient=request.user) | Q(is_broadcast=True))
        .exclude(id__in=read_ids)
        .order_by("-created_at")[:5]
    )
    return {
        "unread_admin_messages": unread,
        "unread_messages": _unread_chat_count(request.user),
    }


def _unread_chat_count(user):
    """Xaridor-sotuvchi suhbatlaridagi o'qilmagan xabarlar soni."""
    from apps.books.models import Message

    return (
        Message.objects.filter(is_read=False)
        .filter(Q(conversation__buyer=user) | Q(conversation__seller=user))
        .exclude(sender=user)
        .count()
    )
