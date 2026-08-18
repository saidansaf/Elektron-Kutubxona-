"""Bot klaviaturalari va matn ko'rinishlari.

Handlerlardan ajratilgan: shunda "nima ko'rsatiladi" va "nima qilinadi"
aralashib ketmaydi.
"""

import telebot
from django.conf import settings
from django.utils.translation import gettext as _

from apps.accounts.models import Role
from apps.books.models import Purchase, Wish

PAGE_SIZE = 5

# Suhbatni har qanday qadamda to'xtatish uchun
CANCEL = "❌ Bekor qilish"
SKIP = "⏭ O'tkazib yuborish"


def money(value):
    """Summani "38 000" ko'rinishida yozadi."""
    return f"{int(value):,}".replace(",", " ")


def menu_labels(role):
    """Pastdagi doimiy menyu tugmalari (rolga qarab)."""
    rows = [["📚 Katalog", "🔍 Qidiruv"]]
    if role == Role.BUYER:
        rows.append(["📖 Kutubxonam", "⭐ Istaklarim"])
        rows.append(["💰 Balans", "💬 Xabarlar"])
    elif role == Role.SELLER:
        rows.append(["➕ Kitob qo'shish", "📚 Kitoblarim"])
        rows.append(["📊 Savdolarim", "💬 Xabarlar"])
        rows.append(["💰 Balans", "⚙️ Sozlamalar"])
    else:
        rows.append(["💰 Balans", "💬 Xabarlar"])
    if role != Role.SELLER:
        rows.append(["⚙️ Sozlamalar", "ℹ️ Yordam"])
    else:
        rows.append(["ℹ️ Yordam"])
    return rows


def main_keyboard(user):
    """Pastdagi doimiy menyu."""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in menu_labels(getattr(user, "role", None)):
        markup.row(*[_(label) for label in row])
    return markup


def cancel_keyboard(extra=None):
    """Suhbat davomidagi klaviatura: qo'shimcha tugmalar + bekor qilish."""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in extra or []:
        markup.row(*row)
    markup.row(_(CANCEL))
    return markup


def book_keyboard(book, user):
    """Kitob kartochkasi ostidagi tugmalar."""
    markup = telebot.types.InlineKeyboardMarkup()
    owned = user and Purchase.objects.filter(buyer=user, book=book).exists()
    is_seller = user and book.seller_id == user.pk

    if owned or is_seller:
        markup.row(
            telebot.types.InlineKeyboardButton(_("📥 Faylni olish"), callback_data=f"get:{book.pk}")
        )
    elif user:
        markup.row(
            telebot.types.InlineKeyboardButton(
                _("💳 Sotib olish · %(price)s") % {"price": money(book.price)},
                callback_data=f"buy:{book.pk}",
            )
        )

    if user and not is_seller:
        wished = Wish.objects.filter(user=user, book=book).exists()
        liked = book.likes.filter(user=user).exists()
        markup.row(
            telebot.types.InlineKeyboardButton(
                _("★ Istaklarda") if wished else _("☆ Istaklarga"),
                callback_data=f"wish:{book.pk}",
            ),
            telebot.types.InlineKeyboardButton(
                ("❤️ " if liked else "🤍 ") + str(book.likes_count),
                callback_data=f"like:{book.pk}",
            ),
        )
        markup.row(
            telebot.types.InlineKeyboardButton(
                _("⭐ Baho berish"), callback_data=f"rate:{book.pk}"
            ),
            telebot.types.InlineKeyboardButton(
                _("💬 Sotuvchiga savol"), callback_data=f"ask:{book.pk}"
            ),
        )

    if is_seller:
        markup.row(
            telebot.types.InlineKeyboardButton(
                _("✏️ Tahrirlash"), callback_data=f"edit:{book.pk}"
            )
        )

    markup.row(
        telebot.types.InlineKeyboardButton(
            _("💬 Sharhlar (%(count)s)") % {"count": book.reviews_count},
            callback_data=f"revs:{book.pk}",
        )
    )
    markup.row(
        telebot.types.InlineKeyboardButton(
            _("🌐 Saytda ochish"), url=f"{settings.SITE_URL}/kitoblar/{book.pk}/"
        )
    )
    return markup


def seller_book_keyboard(book):
    """Sotuvchining o'z kitobini boshqarish tugmalari."""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(_("💰 Narxni o'zgartirish"), callback_data=f"price:{book.pk}"),
    )
    markup.row(
        telebot.types.InlineKeyboardButton(
            _("🚫 Sotuvdan olish") if book.is_active else _("✅ Sotuvga qo'yish"),
            callback_data=f"toggle:{book.pk}",
        ),
        telebot.types.InlineKeyboardButton(_("🗑 O'chirish"), callback_data=f"del:{book.pk}"),
    )
    markup.row(
        telebot.types.InlineKeyboardButton(
            _("🌐 Saytda ochish"), url=f"{settings.SITE_URL}/kitoblar/{book.pk}/"
        )
    )
    return markup


def rating_keyboard(book_pk):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(*[
        telebot.types.InlineKeyboardButton("⭐" * n, callback_data=f"star:{book_pk}:{n}")
        for n in (1, 2, 3)
    ])
    markup.row(*[
        telebot.types.InlineKeyboardButton("⭐" * n, callback_data=f"star:{book_pk}:{n}")
        for n in (4, 5)
    ])
    return markup


def catalog_keyboard(page, total_pages, prefix="cat"):
    markup = telebot.types.InlineKeyboardMarkup()
    buttons = []
    if page > 1:
        buttons.append(telebot.types.InlineKeyboardButton("‹", callback_data=f"{prefix}:{page - 1}"))
    buttons.append(
        telebot.types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop")
    )
    if page < total_pages:
        buttons.append(telebot.types.InlineKeyboardButton("›", callback_data=f"{prefix}:{page + 1}"))
    if buttons:
        markup.row(*buttons)
    return markup


def stars(rating):
    full = int(round(rating or 0))
    return "★" * full + "☆" * (5 - full)


def book_caption(book, user=None):
    """Kitob kartochkasi matni."""
    rating = book.average_rating
    lines = [
        f"<b>{book.title}</b>",
        f"{book.author.full_name}",
        "",
        f"{stars(rating)} {rating} · ❤ {book.likes_count}",
        f"💰 {money(book.price)} " + _("so'm"),
        f"📄 {book.pages} " + _("sahifa"),
    ]
    if book.genre:
        lines.append(f"🏷 {book.genre.name}")
    if not book.is_active:
        lines.append("🚫 " + _("Sotuvda emas"))
    if book.description:
        lines += ["", book.description[:400]]
    return "\n".join(lines)
