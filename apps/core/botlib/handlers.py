"""Telegram bot handlerlari.

Bot saytning ikkinchi yuzi: **xuddi shu ma'lumotlar bazasi** bilan
ishlaydi va sayt qila oladigan hamma ishni qila oladi. Botda kitob
qo'shilsa saytda darrov ko'rinadi, saytda o'zgargani botda ko'rinadi —
oradda hech qanday sinxronizatsiya yo'q, chunki manba bitta.

Pul va xarid mantiqi bu yerda takrorlanmaydi:
    apps/payments/services.py  — to'lov (Payme / Click)
    apps/books/services.py     — kitobni xaridorga biriktirish
    apps/accounts/services.py  — sotuvchining pul yechishi
Sayt ham shu funksiyalarni chaqiradi, shuning uchun qoidalar ikkalasida
bir xil bo'lib qoladi.
"""

import functools
import logging
import traceback

import telebot
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.files.base import ContentFile
from django.db import close_old_connections
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import override

from apps.accounts import services as money_services
from apps.accounts.models import Role, TelegramLink
from apps.books.models import (
    Author,
    Book,
    Conversation,
    Genre,
    Like,
    Message,
    Purchase,
    ReadingProgress,
    Review,
    Wish,
)
from apps.core import telegram as notifier
from apps.payments import services as payment_services

from .state import DialogStore
from .ui import (
    CANCEL,
    PAGE_SIZE,
    SKIP,
    book_caption,
    book_keyboard,
    cancel_keyboard,
    main_keyboard,
    money,
    rating_keyboard,
    seller_book_keyboard,
    stars,
)

logger = logging.getLogger(__name__)

MAX_FILE_MB = 45  # Telegram bot API cheklovi 50 MB, ehtiyot uchun pastroq


def safe_handler(func):
    """Har bir handler uchun himoya qobig'i.

    1. **Baza ulanishi.** telebot handlerlarni alohida iplarda chaqiradi.
       Django bunday iplarda ulanishni o'zi yopmaydi va u eskirib qoladi —
       PostgreSQL'da bir necha daqiqadan keyin "connection already closed"
       xatosi chiqadi.
    2. **Xatolar.** Handler ichida xato chiqsa, telebot uni yutib yuboradi
       va bot foydalanuvchiga hech narsa demay jim qoladi. Endi xato
       jurnalga to'liq tushadi.
    """

    @functools.wraps(func)
    def wrapper(update, *args, **kwargs):
        close_old_connections()
        try:
            return func(update, *args, **kwargs)
        except Exception:
            logger.error("Bot handleri xato berdi:\n%s", traceback.format_exc())
            raise
        finally:
            close_old_connections()

    return wrapper


def user_for(chat_id):
    """Telegram chat'iga ulangan sayt foydalanuvchisi (yoki None)."""
    link = TelegramLink.objects.filter(chat_id=chat_id).select_related("user").first()
    return link.user if link else None


def lang_of(user):
    return getattr(user, "language", "uz") or "uz"


def matches(text, key):
    """Tugma matni uch tildan birida bo'lishi mumkin."""
    for code in ("uz", "ru", "en"):
        with override(code):
            if text == _(key):
                return True
    return False


def register_handlers(bot):  # noqa: C901 - bot menyusi tabiatan katta
    dialogs = DialogStore()

    # ------------------------------------------------------------------
    # Yordamchilar
    # ------------------------------------------------------------------

    def reply(message, text, markup=None, user=None):
        bot.send_message(message.chat.id, text, reply_markup=markup or main_keyboard(user))

    def ask(chat_id, text, extra=None):
        bot.send_message(chat_id, text, reply_markup=cancel_keyboard(extra))

    def finish(chat_id, text, user):
        dialogs.clear(chat_id)
        bot.send_message(chat_id, text, reply_markup=main_keyboard(user))

    def download(file_id):
        """Telegramdagi faylni baytlar ko'rinishida oladi."""
        info = bot.get_file(file_id)
        return bot.download_file(info.file_path)

    def send_book(chat_id, book, user):
        caption = book_caption(book, user)
        keyboard = book_keyboard(book, user)
        if book.cover:
            try:
                with book.cover.open("rb") as image:
                    bot.send_photo(chat_id, image, caption=caption, reply_markup=keyboard)
                return
            except Exception:
                pass  # muqova ochilmasa oddiy matn yuboramiz
        bot.send_message(chat_id, caption, reply_markup=keyboard)

    def send_file(chat_id, book, user):
        """Kitob PDF faylini yuboradi (faqat haqli bo'lsa)."""
        if not book.readable_by(user):
            bot.send_message(chat_id, _("Bu kitob sizda yo'q."))
            return
        if not book.file:
            bot.send_message(chat_id, _("Bu kitobning fayli yuklanmagan."))
            return
        try:
            with book.file.open("rb") as handle:
                bot.send_document(
                    chat_id,
                    handle,
                    visible_file_name=f"{book.title}.pdf",
                    caption=f"📕 {book.title}",
                )
        except Exception as exc:
            logger.warning("Fayl yuborilmadi (%s): %s", book.pk, exc)
            bot.send_message(chat_id, _("Faylni yuborib bo'lmadi. Saytdan yuklab oling."))

    def send_catalog(chat_id, page, user, query=""):
        books = Book.objects.filter(is_active=True).select_related("author", "genre")
        if query:
            books = books.filter(
                Q(title__icontains=query) | Q(author__full_name__icontains=query)
            )
        books = books.order_by("-created_at")

        total = books.count()
        if not total:
            bot.send_message(chat_id, _("Hech narsa topilmadi."))
            return

        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        page = max(1, min(page, total_pages))
        chunk = books[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

        lines = [_("<b>Kitoblar</b> (%(total)s ta)") % {"total": total}, ""]
        markup = telebot.types.InlineKeyboardMarkup()
        for book in chunk:
            lines.append(
                f"<b>{book.title}</b> — {book.author.full_name}\n"
                f"   💰 {money(book.price)} · ★ {book.average_rating or 0}"
            )
            markup.row(
                telebot.types.InlineKeyboardButton(
                    f"📕 {book.title[:40]}", callback_data=f"book:{book.pk}"
                )
            )
        if total_pages > 1:
            nav = []
            if page > 1:
                nav.append(telebot.types.InlineKeyboardButton("‹", callback_data=f"cat:{page - 1}"))
            nav.append(
                telebot.types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop")
            )
            if page < total_pages:
                nav.append(telebot.types.InlineKeyboardButton("›", callback_data=f"cat:{page + 1}"))
            markup.row(*nav)
        bot.send_message(chat_id, "\n".join(lines), reply_markup=markup)

    def require_user(chat_id):
        """Ulangan foydalanuvchi yoki None (va ko'rsatma yuboradi)."""
        user = user_for(chat_id)
        if user is None:
            send_welcome(chat_id)
        return user

    def ask_role_if_needed(chat_id, user):
        """Roli tanlanmagan bo'lsa, darrov tanlashni taklif qiladi.

        Menyu rolga qarab tuziladi: sotuvchida "Kitob qo'shish", xaridorda
        "Kutubxonam" bo'ladi. Rol tanlanmasa foydalanuvchi ikkalasini ham
        ko'rmaydi va tugma yo'qoldi deb o'ylaydi.
        """
        if user is None or user.role_chosen:
            return
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton(
                _("📚 Sotuvchi bo'lish"), callback_data=f"role:{Role.SELLER}"
            ),
            telebot.types.InlineKeyboardButton(
                _("🛒 Xaridor bo'lish"), callback_data=f"role:{Role.BUYER}"
            ),
        )
        bot.send_message(
            chat_id,
            _(
                "Rolingiz hali tanlanmagan. Menyu shunga qarab tuziladi:\n\n"
                "📚 <b>Sotuvchi</b> — kitob qo'shadi va sotadi\n"
                "🛒 <b>Xaridor</b> — kitob sotib oladi va o'qiydi\n\n"
                "Keyin Sozlamalardan o'zgartirsa bo'ladi."
            ),
            reply_markup=markup,
        )

    def send_welcome(chat_id):
        bot.send_message(
            chat_id,
            _(
                "📚 <b>Elektron Kutubxona</b>\n\n"
                "Botdan foydalanish uchun saytdagi hisobingizni ulang:\n\n"
                "• <b>/kirish</b> — login va parol bilan\n"
                "• yoki saytdan olingan 6 xonali kodni yuboring\n\n"
                "Sayt: %(site)s"
            )
            % {"site": settings.SITE_URL},
            reply_markup=telebot.types.ReplyKeyboardRemove(),
        )

    # ------------------------------------------------------------------
    # Kelgan xabarlarni jurnalga yozish
    # ------------------------------------------------------------------

    @bot.middleware_handler(update_types=["message"])
    def log_incoming(bot_instance, message):
        """Bot javob bermasa, birinchi savol shu: xabar yetib kelyaptimi?

        Jurnalda ko'rinsa — muammo kodda, ko'rinmasa — token yoki tarmoqda.
        """
        logger.info(
            "Kelgan xabar: chat=%s user=@%s matn=%r",
            message.chat.id,
            message.from_user.username,
            (message.text or "")[:60],
        )

    # ------------------------------------------------------------------
    # Buyruqlar — suhbat ichida ham ishlaydi (chiqib ketish yo'li)
    # ------------------------------------------------------------------

    @bot.message_handler(commands=["start"])
    @safe_handler
    def on_start(message):
        dialogs.clear(message.chat.id)
        user = user_for(message.chat.id)
        if not user:
            send_welcome(message.chat.id)
            return
        with override(lang_of(user)):
            reply(
                message,
                _("Salom, <b>%(name)s</b>! 👋\n\nQuyidagi menyudan foydalaning.")
                % {"name": user.username},
                user=user,
            )
            ask_role_if_needed(message.chat.id, user)

    @bot.message_handler(commands=["help"])
    @safe_handler
    def on_help(message):
        user = user_for(message.chat.id)
        with override(lang_of(user)):
            role_help = ""
            if user and user.role == Role.SELLER:
                role_help = _(
                    "\n<b>Sotuvchi uchun</b>\n"
                    "➕ Kitob qo'shish — botdan kitob joylash\n"
                    "📚 Kitoblarim — narx, sotuvdan olish, o'chirish\n"
                    "📊 Savdolarim — daromad va pul yechish\n"
                )
            elif user:
                role_help = _(
                    "\n<b>Xaridor uchun</b>\n"
                    "📖 Kutubxonam — sotib olingan kitoblar va PDF\n"
                    "⭐ Istaklarim — saqlab qo'yilgan kitoblar\n"
                    "🧾 To'lovlarim — to'lovlar tarixi\n"
                )
            reply(
                message,
                _(
                    "<b>Bot sayt bilan bir xil ishlaydi</b>\n"
                    "Botda qilgan ishingiz saytda ham ko'rinadi.\n\n"
                    "📚 Katalog — kitoblarni ko'rish\n"
                    "🔍 Qidiruv — nom yoki muallif bo'yicha\n"
                    "💬 Xabarlar — sotuvchi bilan yozishmalar\n"
                    "⚙️ Sozlamalar — til, bildirishnoma, hisob\n"
                    "%(role)s\n"
                    "<b>Buyruqlar</b>\n"
                    "/kirish — login va parol bilan kirish\n"
                    "/chiqish — hisobni uzish\n"
                    "/bekor — boshlangan amalni to'xtatish\n\n"
                    "Sayt: %(site)s"
                )
                % {"role": role_help, "site": settings.SITE_URL},
                user=user,
            )

    @bot.message_handler(commands=["bekor", "cancel"])
    @safe_handler
    def on_cancel_command(message):
        user = user_for(message.chat.id)
        with override(lang_of(user)):
            if dialogs.active(message.chat.id):
                finish(message.chat.id, _("Bekor qilindi."), user)
            else:
                reply(message, _("Hozir bekor qiladigan amal yo'q."), user=user)

    @bot.message_handler(commands=["kirish", "login"])
    @safe_handler
    def on_login_command(message):
        if user_for(message.chat.id):
            user = user_for(message.chat.id)
            with override(lang_of(user)):
                reply(message, _("Siz allaqachon kirgansiz."), user=user)
            return
        dialogs.start(message.chat.id, "login", "username")
        ask(message.chat.id, _("Saytdagi foydalanuvchi nomingizni yozing:"))

    @bot.message_handler(commands=["chiqish", "unlink", "logout"])
    @safe_handler
    def on_unlink(message):
        user = user_for(message.chat.id)
        if not user:
            return
        dialogs.clear(message.chat.id)
        TelegramLink.objects.filter(chat_id=message.chat.id).update(
            chat_id=None, code="", linked_at=None
        )
        with override(lang_of(user)):
            bot.send_message(
                message.chat.id,
                _("Hisob uzildi. Qayta ulash uchun /kirish yozing."),
                reply_markup=telebot.types.ReplyKeyboardRemove(),
            )

    # ------------------------------------------------------------------
    # Suhbat yo'naltirgichi — barcha ko'p qadamli amallar shu yerdan o'tadi
    # ------------------------------------------------------------------

    @bot.message_handler(
        func=lambda m: dialogs.active(m.chat.id),
        content_types=["text", "photo", "document"],
    )
    @safe_handler
    def on_dialog(message):
        dialog = dialogs.get(message.chat.id)
        if dialog is None:
            return
        dialog.touch()

        user = user_for(message.chat.id)
        text = (message.text or "").strip()

        # "Bekor qilish" har qanday qadamda ishlaydi
        if text and matches(text, CANCEL):
            with override(lang_of(user)):
                finish(message.chat.id, _("Bekor qilindi."), user)
            return

        with override(lang_of(user)):
            handler = DIALOGS.get(dialog.name)
            if handler is None:
                dialogs.clear(message.chat.id)
                return
            handler(message, dialog, user, text)

    # --- Kirish (login/parol) ---

    def dialog_login(message, dialog, user, text):
        chat_id = message.chat.id

        if dialog.step == "username":
            if not text:
                ask(chat_id, _("Foydalanuvchi nomini yozing:"))
                return
            dialog.data["username"] = text
            dialog.step = "password"
            ask(chat_id, _("Endi parolingizni yozing:"))
            return

        if dialog.step == "password":
            # Parol chat tarixida qolib ketmasin: xabarni darrov o'chiramiz.
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                logger.info("Parol xabari o'chirilmadi (bot huquqi yetmasligi mumkin)")

            account = authenticate(username=dialog.data.get("username"), password=text)
            if account is None:
                dialogs.clear(chat_id)
                bot.send_message(
                    chat_id,
                    _("Login yoki parol noto'g'ri. Qayta urinish: /kirish"),
                    reply_markup=telebot.types.ReplyKeyboardRemove(),
                )
                return
            if getattr(account, "is_blocked", False):
                dialogs.clear(chat_id)
                bot.send_message(chat_id, _("Hisobingiz bloklangan."))
                return

            # Bitta hisob bitta Telegramga ulanadi: eski ulanish uziladi.
            TelegramLink.objects.filter(chat_id=chat_id).exclude(user=account).update(
                chat_id=None, code="", linked_at=None
            )
            link, _created = TelegramLink.objects.get_or_create(user=account)
            link.chat_id = chat_id
            link.username = (message.from_user.username or "")[:64]
            link.code = ""
            link.linked_at = timezone.now()
            link.save()

            dialogs.clear(chat_id)
            with override(lang_of(account)):
                bot.send_message(
                    chat_id,
                    _("✅ Xush kelibsiz, <b>%(name)s</b>!") % {"name": account.username},
                    reply_markup=main_keyboard(account),
                )
                ask_role_if_needed(chat_id, account)

    # --- Kitob qo'shish ---

    def dialog_book(message, dialog, user, text):  # noqa: C901 - ko'p qadamli forma
        chat_id = message.chat.id
        data = dialog.data
        step = dialog.step

        if step == "title":
            if not text:
                ask(chat_id, _("Kitob nomini yozing:"))
                return
            data["title"] = text[:255]
            dialog.step = "author"
            recent = list(Author.objects.order_by("-created_at")[:6].values_list("full_name", flat=True))
            rows = [[name] for name in recent]
            ask(chat_id, _("Muallif ismini yozing (yoki ro'yxatdan tanlang):"), rows)
            return

        if step == "author":
            if not text:
                ask(chat_id, _("Muallif ismini yozing:"))
                return
            data["author"] = text[:150]
            dialog.step = "genre"
            names = list(Genre.objects.order_by("name")[:8].values_list("name", flat=True))
            rows = [names[i : i + 2] for i in range(0, len(names), 2)]
            rows.append([_(SKIP)])
            ask(chat_id, _("Janrni tanlang yoki yangisini yozing:"), rows)
            return

        if step == "genre":
            data["genre"] = "" if matches(text, SKIP) else text[:100]
            dialog.step = "language"
            ask(chat_id, _("Kitob tili:"), [["O'zbekcha", "Русский", "English"]])
            return

        if step == "language":
            codes = {"o'zbekcha": "uz", "русский": "ru", "english": "en"}
            data["language"] = codes.get(text.casefold(), "uz")
            dialog.step = "pages"
            ask(chat_id, _("Sahifalar soni (raqam):"))
            return

        if step == "pages":
            digits = "".join(ch for ch in text if ch.isdigit())
            if not digits:
                ask(chat_id, _("Sahifalar sonini raqam bilan yozing. Masalan: 250"))
                return
            data["pages"] = min(int(digits), 100000)
            dialog.step = "price"
            ask(chat_id, _("Narxi (so'm):"))
            return

        if step == "price":
            try:
                data["price"] = money_services.parse_amount(text)
            except money_services.MoneyError as exc:
                ask(chat_id, str(exc))
                return
            dialog.step = "description"
            ask(chat_id, _("Qisqacha tavsif yozing:"), [[_(SKIP)]])
            return

        if step == "description":
            data["description"] = "" if matches(text, SKIP) else text[:2000]
            dialog.step = "cover"
            ask(chat_id, _("Muqova rasmini yuboring:"), [[_(SKIP)]])
            return

        if step == "cover":
            if message.content_type == "photo":
                try:
                    data["cover"] = download(message.photo[-1].file_id)
                except Exception:
                    logger.warning("Muqova yuklab olinmadi", exc_info=True)
                    ask(chat_id, _("Rasmni olib bo'lmadi. Qayta yuboring yoki o'tkazib yuboring."), [[_(SKIP)]])
                    return
            elif not (text and matches(text, SKIP)):
                ask(chat_id, _("Rasm yuboring yoki «%(skip)s» tugmasini bosing.") % {"skip": _(SKIP)}, [[_(SKIP)]])
                return
            dialog.step = "file"
            ask(chat_id, _("Endi kitobning PDF faylini yuboring:"), [[_(SKIP)]])
            return

        if step == "file":
            if message.content_type == "document":
                name = (message.document.file_name or "").casefold()
                if not name.endswith(".pdf"):
                    ask(chat_id, _("Faqat PDF fayl qabul qilinadi."), [[_(SKIP)]])
                    return
                if (message.document.file_size or 0) > MAX_FILE_MB * 1024 * 1024:
                    ask(
                        chat_id,
                        _("Fayl juda katta (%(max)s MB dan oshmasin). Saytdan yuklang.")
                        % {"max": MAX_FILE_MB},
                        [[_(SKIP)]],
                    )
                    return
                try:
                    data["file"] = download(message.document.file_id)
                except Exception:
                    logger.warning("PDF yuklab olinmadi", exc_info=True)
                    ask(chat_id, _("Faylni olib bo'lmadi. Qayta yuboring."), [[_(SKIP)]])
                    return
            elif not (text and matches(text, SKIP)):
                ask(chat_id, _("PDF yuboring yoki «%(skip)s» tugmasini bosing.") % {"skip": _(SKIP)}, [[_(SKIP)]])
                return

            book = save_book(user, data)
            dialogs.clear(chat_id)
            bot.send_message(
                chat_id,
                _("✅ <b>%(title)s</b> qo'shildi va saytda ko'rinmoqda.") % {"title": book.title},
                reply_markup=main_keyboard(user),
            )
            send_book(chat_id, book, user)

    def save_book(seller, data):
        """Botdan kelgan ma'lumotlardan kitob yaratadi.

        Muallif va janr nomi bo'yicha qidiriladi: sotuvchi mavjud
        muallifni yozsa yangi nusxa yaratilmaydi.
        """
        author = Author.objects.filter(full_name__iexact=data["author"]).first()
        if author is None:
            author = Author.objects.create(full_name=data["author"], created_by=seller)

        genre = None
        if data.get("genre"):
            genre = Genre.objects.filter(name__iexact=data["genre"]).first()
            if genre is None:
                genre = Genre.objects.create(name=data["genre"])

        book = Book(
            title=data["title"],
            author=author,
            genre=genre,
            seller=seller,
            language=data.get("language", "uz"),
            pages=data.get("pages") or 1,
            price=data["price"],
            description=data.get("description", ""),
        )
        if data.get("cover"):
            book.cover.save(f"cover-{timezone.now():%Y%m%d%H%M%S}.jpg", ContentFile(data["cover"]), save=False)
        if data.get("file"):
            book.file.save(f"book-{timezone.now():%Y%m%d%H%M%S}.pdf", ContentFile(data["file"]), save=False)
        book.save()
        return book

    # --- Narxni o'zgartirish ---

    def dialog_price(message, dialog, user, text):
        book = Book.objects.filter(pk=dialog.data["book"], seller=user).first()
        if book is None:
            finish(message.chat.id, _("Kitob topilmadi."), user)
            return
        try:
            book.price = money_services.parse_amount(text)
        except money_services.MoneyError as exc:
            ask(message.chat.id, str(exc))
            return
        book.save(update_fields=["price"])
        finish(
            message.chat.id,
            _("✅ Yangi narx: %(price)s so'm") % {"price": money(book.price)},
            user,
        )

    # --- Sharh ---

    def dialog_review(message, dialog, user, text):
        book = Book.objects.filter(pk=dialog.data["book"]).first()
        if book is None:
            finish(message.chat.id, _("Kitob topilmadi."), user)
            return
        comment = "" if matches(text, SKIP) else text[:2000]
        Review.objects.update_or_create(
            book=book,
            buyer=user,
            defaults={"rating": dialog.data["rating"], "comment": comment},
        )
        finish(message.chat.id, _("✅ Sharhingiz saqlandi. Saytda ham ko'rinadi."), user)

    # --- Sotuvchiga savol / suhbatda javob ---

    def dialog_message(message, dialog, user, text):
        if not text:
            ask(message.chat.id, _("Xabar matnini yozing:"))
            return

        conversation = Conversation.objects.filter(pk=dialog.data["conversation"]).first()
        if conversation is None:
            finish(message.chat.id, _("Suhbat topilmadi."), user)
            return

        body = text[:4000]
        Message.objects.create(conversation=conversation, sender=user, text=body)
        conversation.save(update_fields=["updated_at"])
        finish(message.chat.id, _("✅ Xabar yuborildi."), user)
        notifier.notify_new_message(conversation, user, body)

    # --- Pul yechish ---

    def dialog_withdraw(message, dialog, user, text):
        chat_id = message.chat.id
        if dialog.step == "amount":
            try:
                dialog.data["amount"] = money_services.parse_amount(text)
            except money_services.MoneyError as exc:
                ask(chat_id, str(exc))
                return
            dialog.step = "card"
            ask(chat_id, _("Pul o'tkaziladigan karta raqamini yozing:"))
            return

        if dialog.step == "card":
            try:
                money_services.request_withdrawal(user, dialog.data["amount"], text)
            except money_services.MoneyError as exc:
                ask(chat_id, str(exc))
                return
            finish(
                chat_id,
                _(
                    "✅ So'rov yuborildi. Administrator tasdiqlagach pul kartangizga o'tkaziladi.\n"
                    "Daromad: %(balance)s so'm"
                )
                % {"balance": money(user.balance)},
                user,
            )

    # --- Qidiruv ---

    def dialog_search(message, dialog, user, text):
        dialogs.clear(message.chat.id)
        if not text:
            reply(message, _("Qidiruv bekor qilindi."), user=user)
            return
        send_catalog(message.chat.id, 1, user, text)

    DIALOGS = {
        "login": dialog_login,
        "book": dialog_book,
        "price": dialog_price,
        "review": dialog_review,
        "message": dialog_message,
        "withdraw": dialog_withdraw,
        "search": dialog_search,
    }

    # ------------------------------------------------------------------
    # Ulash kodi
    # ------------------------------------------------------------------

    @bot.message_handler(regexp=r"^\d{6}$")
    @safe_handler
    def on_code(message):
        if user_for(message.chat.id):
            return  # allaqachon ulangan

        code = message.text.strip()
        link = (
            TelegramLink.objects.filter(code=code, chat_id__isnull=True)
            .select_related("user")
            .first()
        )
        if link is None or not link.code_is_fresh():
            bot.send_message(
                message.chat.id,
                _("Kod noto'g'ri yoki muddati o'tgan. Saytdan yangi kod oling."),
            )
            return

        link.chat_id = message.chat.id
        link.username = (message.from_user.username or "")[:64]
        link.code = ""
        link.linked_at = timezone.now()
        link.save()

        with override(lang_of(link.user)):
            bot.send_message(
                message.chat.id,
                _("✅ Hisob ulandi: <b>%(name)s</b>") % {"name": link.user.username},
                reply_markup=main_keyboard(link.user),
            )
            ask_role_if_needed(message.chat.id, link.user)

    # ------------------------------------------------------------------
    # Menyu tugmalari
    # ------------------------------------------------------------------

    def menu(key):
        """Menyu tugmasi uchun handler yozishni qisqartiradi."""
        return lambda m: bool(m.text) and matches(m.text, key)

    @bot.message_handler(func=menu("📚 Katalog"))
    @safe_handler
    def on_catalog(message):
        user = user_for(message.chat.id)
        with override(lang_of(user)):
            send_catalog(message.chat.id, 1, user)

    @bot.message_handler(func=menu("🔍 Qidiruv"))
    @safe_handler
    def on_search_prompt(message):
        user = user_for(message.chat.id)
        dialogs.start(message.chat.id, "search", "query")
        with override(lang_of(user)):
            ask(message.chat.id, _("Kitob nomi yoki muallif ismini yozing:"))

    @bot.message_handler(func=menu("📖 Kutubxonam"))
    @safe_handler
    def on_library(message):
        user = require_user(message.chat.id)
        if not user:
            return
        purchases = Purchase.objects.filter(buyer=user).select_related("book", "book__author")
        with override(lang_of(user)):
            if not purchases:
                reply(message, _("Hali kitob sotib olmagansiz."), user=user)
                return
            progress = {p.book_id: p for p in ReadingProgress.objects.filter(user=user)}
            markup = telebot.types.InlineKeyboardMarkup()
            lines = [_("<b>Mening kutubxonam</b>"), ""]
            for purchase in purchases:
                book = purchase.book
                state = progress.get(book.pk)
                percent = f" · {state.percent}%" if state else ""
                lines.append(f"📕 <b>{book.title}</b> — {book.author.full_name}{percent}")
                markup.row(
                    telebot.types.InlineKeyboardButton(
                        f"📥 {book.title[:40]}", callback_data=f"get:{book.pk}"
                    )
                )
            bot.send_message(message.chat.id, "\n".join(lines), reply_markup=markup)

    @bot.message_handler(func=menu("⭐ Istaklarim"))
    @safe_handler
    def on_wishlist(message):
        user = require_user(message.chat.id)
        if not user:
            return
        wishes = Wish.objects.filter(user=user, book__is_active=True).select_related(
            "book", "book__author"
        )
        with override(lang_of(user)):
            if not wishes:
                reply(message, _("Istaklar ro'yxati bo'sh. Katalogdan kitob qo'shing."), user=user)
                return
            markup = telebot.types.InlineKeyboardMarkup()
            lines = [_("<b>Istaklarim</b>"), ""]
            for wish in wishes:
                book = wish.book
                lines.append(f"☆ <b>{book.title}</b> — {money(book.price)}")
                markup.row(
                    telebot.types.InlineKeyboardButton(
                        f"📕 {book.title[:40]}", callback_data=f"book:{book.pk}"
                    )
                )
            bot.send_message(message.chat.id, "\n".join(lines), reply_markup=markup)

    @bot.message_handler(func=menu("💰 Daromadim"))
    @safe_handler
    def on_balance(message):
        """Sotuvchining daromadi. Xaridorda hisob yo'q — u kartadan to'laydi."""
        user = require_user(message.chat.id)
        if not user:
            return
        user.refresh_from_db()
        with override(lang_of(user)):
            if user.role != Role.SELLER:
                reply(message, _("Bu bo'lim sotuvchilar uchun."), user=user)
                return
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton(_("🏧 Pul yechish"), callback_data="withdraw")
            )
            bot.send_message(
                message.chat.id,
                _("💰 <b>Daromadingiz:</b> %(amount)s so'm") % {"amount": money(user.balance)},
                reply_markup=markup,
            )

    @bot.message_handler(func=menu("🧾 To'lovlarim"))
    @safe_handler
    def on_my_payments(message):
        """Xaridorning to'lovlari tarixi."""
        user = require_user(message.chat.id)
        if not user:
            return
        from apps.payments.models import Payment

        with override(lang_of(user)):
            payments = Payment.objects.filter(user=user).select_related("book")[:10]
            if not payments:
                reply(message, _("Hozircha to'lov qilinmagan."), user=user)
                return
            lines = [_("<b>To'lovlarim</b>"), ""]
            for item in payments:
                title = item.book.title if item.book else "—"
                lines.append(
                    f"{item.created_at:%Y-%m-%d} · <b>{title}</b>\n"
                    f"   {money(item.amount)} so'm · {item.get_status_display()}"
                )
            reply(message, "\n".join(lines), user=user)

    @bot.message_handler(func=menu("➕ Kitob qo'shish"))
    @safe_handler
    def on_book_add(message):
        user = require_user(message.chat.id)
        if not user:
            return
        with override(lang_of(user)):
            if user.role != Role.SELLER:
                reply(message, _("Kitob qo'shish uchun sotuvchi rejimiga o'ting."), user=user)
                return
            dialogs.start(message.chat.id, "book", "title")
            ask(message.chat.id, _("Kitob nomini yozing:"))

    @bot.message_handler(func=menu("📚 Kitoblarim"))
    @safe_handler
    def on_my_books(message):
        user = require_user(message.chat.id)
        if not user:
            return
        with override(lang_of(user)):
            books = Book.objects.filter(seller=user).select_related("author")
            if not books:
                reply(message, _("Hali kitob qo'shmagansiz."), user=user)
                return
            markup = telebot.types.InlineKeyboardMarkup()
            lines = [_("<b>Mening kitoblarim</b>"), ""]
            for book in books:
                mark = "" if book.is_active else " 🚫"
                sold = book.purchases.count()
                lines.append(
                    f"📕 <b>{book.title}</b>{mark}\n"
                    + _("   %(price)s so'm · %(sold)s marta sotilgan")
                    % {"price": money(book.price), "sold": sold}
                )
                markup.row(
                    telebot.types.InlineKeyboardButton(
                        f"⚙️ {book.title[:40]}", callback_data=f"mybook:{book.pk}"
                    )
                )
            bot.send_message(message.chat.id, "\n".join(lines), reply_markup=markup)

    @bot.message_handler(func=menu("📊 Savdolarim"))
    @safe_handler
    def on_sales(message):
        user = require_user(message.chat.id)
        if not user or user.role != Role.SELLER:
            return
        sales = Purchase.objects.filter(book__seller=user).select_related("book", "buyer")
        total = sum(sale.price_paid for sale in sales)
        with override(lang_of(user)):
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton(_("🏧 Pul yechish"), callback_data="withdraw")
            )
            markup.row(
                telebot.types.InlineKeyboardButton(
                    _("📊 To'liq kabinet"), url=f"{settings.SITE_URL}/kitoblar/kabinet/"
                )
            )
            lines = [
                _("<b>Savdo hisoboti</b>"),
                "",
                _("Sotilgan: %(count)s ta") % {"count": len(sales)},
                _("Daromad: %(amount)s so'm") % {"amount": money(total)},
                _("Hisobda: %(amount)s so'm") % {"amount": money(user.balance)},
            ]
            if sales:
                lines += ["", _("<b>Oxirgi sotuvlar:</b>")]
                for sale in sales[:5]:
                    lines.append(f"• {sale.book.title} — {money(sale.price_paid)}")
            bot.send_message(message.chat.id, "\n".join(lines), reply_markup=markup)

    @bot.message_handler(func=menu("💬 Xabarlar"))
    @safe_handler
    def on_conversations(message):
        user = require_user(message.chat.id)
        if not user:
            return
        with override(lang_of(user)):
            items = (
                Conversation.objects.filter(Q(buyer=user) | Q(seller=user))
                .select_related("book", "buyer", "seller")
                .order_by("-updated_at")[:15]
            )
            if not items:
                reply(
                    message,
                    _("Hali yozishma yo'q. Kitob sahifasidan sotuvchiga savol bering."),
                    user=user,
                )
                return
            markup = telebot.types.InlineKeyboardMarkup()
            lines = [_("<b>Xabarlar</b>"), ""]
            for conversation in items:
                other = conversation.other_side(user)
                unread = conversation.unread_count(user)
                badge = f" ({unread})" if unread else ""
                lines.append(f"💬 <b>{other.username}</b>{badge} — {conversation.book.title}")
                markup.row(
                    telebot.types.InlineKeyboardButton(
                        f"{other.username}{badge} · {conversation.book.title[:24]}",
                        callback_data=f"conv:{conversation.pk}",
                    )
                )
            bot.send_message(message.chat.id, "\n".join(lines), reply_markup=markup)

    @bot.message_handler(func=menu("⚙️ Sozlamalar"))
    @safe_handler
    def on_settings(message):
        user = require_user(message.chat.id)
        if not user:
            return
        with override(lang_of(user)):
            send_settings(message.chat.id, user)

    def send_settings(chat_id, user):
        link = TelegramLink.objects.filter(user=user).first()
        notifications = bool(link and link.notifications)
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang:uz"),
            telebot.types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
            telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
        )
        markup.row(
            telebot.types.InlineKeyboardButton(
                _("🔔 Bildirishnoma: yoqilgan") if notifications else _("🔕 Bildirishnoma: o'chiq"),
                callback_data="notif",
            )
        )
        # Ikkala rol ham tugma bo'lib chiqadi (hozirgisidan tashqari).
        # Ilgari faqat bittasi ko'rsatilardi va roli tanlanmagan hisob
        # (masalan administrator) botdan sotuvchiga umuman o'ta olmasdi —
        # "Kitob qo'shish" tugmasi esa faqat sotuvchida bo'lgani uchun
        # yo'qolib qolardi.
        role_buttons = [
            telebot.types.InlineKeyboardButton(
                _("🔄 %(role)s bo'lish") % {"role": Role(role).label},
                callback_data=f"role:{role}",
            )
            for role in (Role.SELLER, Role.BUYER)
            if role != user.role
        ]
        if role_buttons:
            markup.row(*role_buttons)
        markup.row(
            telebot.types.InlineKeyboardButton(
                _("🌐 Saytdagi sozlamalar"), url=f"{settings.SITE_URL}/hisobim/sozlamalar/"
            )
        )
        bot.send_message(
            chat_id,
            _(
                "<b>Sozlamalar</b>\n\n"
                "Hisob: <b>%(name)s</b>\n"
                "Rol: %(role)s\n"
                "Til: %(lang)s"
            )
            % {
                "name": user.username,
                "role": user.get_role_display() if user.role_chosen else "—",
                "lang": dict(settings.LANGUAGES).get(lang_of(user), "—"),
            },
            reply_markup=markup,
        )

    @bot.message_handler(func=menu("ℹ️ Yordam"))
    @safe_handler
    def on_help_button(message):
        on_help(message)

    # ------------------------------------------------------------------
    # Inline tugmalar
    # ------------------------------------------------------------------

    def callback_user(call):
        user = user_for(call.message.chat.id)
        if user is None:
            bot.answer_callback_query(call.id, _("Avval hisobingizni ulang."), show_alert=True)
        return user

    @bot.callback_query_handler(func=lambda c: c.data.startswith("cat:"))
    @safe_handler
    def on_catalog_page(call):
        page = int(call.data.split(":")[1])
        bot.answer_callback_query(call.id)
        user = user_for(call.message.chat.id)
        with override(lang_of(user)):
            send_catalog(call.message.chat.id, page, user)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("book:"))
    @safe_handler
    def on_book(call):
        user = user_for(call.message.chat.id)
        book = Book.objects.filter(pk=int(call.data.split(":")[1])).first()
        bot.answer_callback_query(call.id)
        if book:
            with override(lang_of(user)):
                send_book(call.message.chat.id, book, user)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("mybook:"))
    @safe_handler
    def on_my_book(call):
        user = callback_user(call)
        if not user:
            return
        book = Book.objects.filter(pk=int(call.data.split(":")[1]), seller=user).first()
        bot.answer_callback_query(call.id)
        if not book:
            return
        with override(lang_of(user)):
            sold = book.purchases.count()
            earned = sum(p.price_paid for p in book.purchases.all())
            bot.send_message(
                call.message.chat.id,
                _(
                    "<b>%(title)s</b>\n"
                    "Narx: %(price)s so'm\n"
                    "Sotilgan: %(sold)s ta\n"
                    "Daromad: %(earned)s so'm\n"
                    "Holat: %(state)s"
                )
                % {
                    "title": book.title,
                    "price": money(book.price),
                    "sold": sold,
                    "earned": money(earned),
                    "state": _("sotuvda") if book.is_active else _("sotuvda emas"),
                },
                reply_markup=seller_book_keyboard(book),
            )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("edit:"))
    @safe_handler
    def on_edit(call):
        on_my_book(call)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("price:"))
    @safe_handler
    def on_price(call):
        user = callback_user(call)
        if not user:
            return
        book = Book.objects.filter(pk=int(call.data.split(":")[1]), seller=user).first()
        bot.answer_callback_query(call.id)
        if not book:
            return
        dialogs.start(call.message.chat.id, "price", "amount", {"book": book.pk})
        with override(lang_of(user)):
            ask(
                call.message.chat.id,
                _("«%(title)s» uchun yangi narxni yozing (hozirgi: %(price)s):")
                % {"title": book.title, "price": money(book.price)},
            )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("toggle:"))
    @safe_handler
    def on_toggle(call):
        user = callback_user(call)
        if not user:
            return
        book = Book.objects.filter(pk=int(call.data.split(":")[1]), seller=user).first()
        if not book:
            bot.answer_callback_query(call.id)
            return
        book.is_active = not book.is_active
        book.save(update_fields=["is_active"])
        with override(lang_of(user)):
            bot.answer_callback_query(
                call.id, _("Sotuvga qo'yildi") if book.is_active else _("Sotuvdan olindi")
            )
            try:
                bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=seller_book_keyboard(book),
                )
            except Exception:
                pass

    @bot.callback_query_handler(func=lambda c: c.data.startswith("del:"))
    @safe_handler
    def on_delete_ask(call):
        user = callback_user(call)
        if not user:
            return
        book = Book.objects.filter(pk=int(call.data.split(":")[1]), seller=user).first()
        bot.answer_callback_query(call.id)
        if not book:
            return
        with override(lang_of(user)):
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton(_("Ha, o'chirilsin"), callback_data=f"delok:{book.pk}"),
                telebot.types.InlineKeyboardButton(_("Yo'q"), callback_data="noop"),
            )
            bot.send_message(
                call.message.chat.id,
                _("«%(title)s» butunlay o'chirilsinmi?") % {"title": book.title},
                reply_markup=markup,
            )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("delok:"))
    @safe_handler
    def on_delete(call):
        user = callback_user(call)
        if not user:
            return
        book = Book.objects.filter(pk=int(call.data.split(":")[1]), seller=user).first()
        if not book:
            bot.answer_callback_query(call.id)
            return
        title = book.title
        book.delete()
        with override(lang_of(user)):
            bot.answer_callback_query(call.id, _("O'chirildi"))
            bot.send_message(
                call.message.chat.id, _("🗑 «%(title)s» o'chirildi.") % {"title": title}
            )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("wish:"))
    @safe_handler
    def on_wish(call):
        user = callback_user(call)
        if not user:
            return
        book = Book.objects.filter(pk=int(call.data.split(":")[1])).first()
        if not book:
            bot.answer_callback_query(call.id)
            return
        with override(lang_of(user)):
            wish = Wish.objects.filter(user=user, book=book).first()
            if wish:
                wish.delete()
                bot.answer_callback_query(call.id, _("Istaklardan olib tashlandi"))
            else:
                Wish.objects.create(user=user, book=book)
                bot.answer_callback_query(call.id, _("Istaklarga qo'shildi"))
            try:
                bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=book_keyboard(book, user),
                )
            except Exception:
                pass

    @bot.callback_query_handler(func=lambda c: c.data.startswith("like:"))
    @safe_handler
    def on_like(call):
        user = callback_user(call)
        if not user:
            return
        book = Book.objects.filter(pk=int(call.data.split(":")[1])).first()
        if not book:
            bot.answer_callback_query(call.id)
            return
        with override(lang_of(user)):
            like = Like.objects.filter(user=user, book=book).first()
            if like:
                like.delete()
                bot.answer_callback_query(call.id, _("Yoqtirish olib tashlandi"))
            else:
                Like.objects.create(user=user, book=book)
                bot.answer_callback_query(call.id, _("Yoqtirdingiz"))
            try:
                bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=book_keyboard(book, user),
                )
            except Exception:
                pass

    @bot.callback_query_handler(func=lambda c: c.data.startswith("rate:"))
    @safe_handler
    def on_rate(call):
        user = callback_user(call)
        if not user:
            return
        book_pk = int(call.data.split(":")[1])
        bot.answer_callback_query(call.id)
        with override(lang_of(user)):
            bot.send_message(
                call.message.chat.id,
                _("Nechta yulduz berasiz?"),
                reply_markup=rating_keyboard(book_pk),
            )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("star:"))
    @safe_handler
    def on_star(call):
        user = callback_user(call)
        if not user:
            return
        _prefix, book_pk, rating = call.data.split(":")
        bot.answer_callback_query(call.id)
        dialogs.start(
            call.message.chat.id, "review", "comment", {"book": int(book_pk), "rating": int(rating)}
        )
        with override(lang_of(user)):
            ask(call.message.chat.id, _("Fikringizni yozing:"), [[_(SKIP)]])

    @bot.callback_query_handler(func=lambda c: c.data.startswith("revs:"))
    @safe_handler
    def on_reviews(call):
        user = user_for(call.message.chat.id)
        book = Book.objects.filter(pk=int(call.data.split(":")[1])).first()
        bot.answer_callback_query(call.id)
        if not book:
            return
        with override(lang_of(user)):
            reviews = book.reviews.select_related("buyer")[:10]
            if not reviews:
                bot.send_message(call.message.chat.id, _("Bu kitobga hali sharh yozilmagan."))
                return
            lines = [_("<b>Sharhlar — %(title)s</b>") % {"title": book.title}, ""]
            for review in reviews:
                lines.append(f"{stars(review.rating)} <b>{review.buyer.username}</b>")
                if review.comment:
                    lines.append(review.comment[:300])
                lines.append("")
            bot.send_message(call.message.chat.id, "\n".join(lines))

    @bot.callback_query_handler(func=lambda c: c.data.startswith("ask:"))
    @safe_handler
    def on_ask_seller(call):
        user = callback_user(call)
        if not user:
            return
        book = Book.objects.filter(pk=int(call.data.split(":")[1])).select_related("seller").first()
        bot.answer_callback_query(call.id)
        if not book:
            return
        with override(lang_of(user)):
            if book.seller_id == user.pk:
                bot.send_message(call.message.chat.id, _("Bu sizning kitobingiz."))
                return
            conversation, _created = Conversation.objects.get_or_create(
                book=book, buyer=user, defaults={"seller": book.seller}
            )
            dialogs.start(
                call.message.chat.id, "message", "text", {"conversation": conversation.pk}
            )
            ask(
                call.message.chat.id,
                _("«%(title)s» bo'yicha savolingizni yozing:") % {"title": book.title},
            )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("conv:"))
    @safe_handler
    def on_conversation(call):
        user = callback_user(call)
        if not user:
            return
        conversation = (
            Conversation.objects.filter(pk=int(call.data.split(":")[1]))
            .filter(Q(buyer=user) | Q(seller=user))
            .select_related("book", "buyer", "seller")
            .first()
        )
        bot.answer_callback_query(call.id)
        if not conversation:
            return

        # Ochilgan suhbatdagi xabarlar o'qilgan deb belgilanadi — saytda ham
        # shu holat ko'rinadi.
        conversation.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)

        with override(lang_of(user)):
            other = conversation.other_side(user)
            lines = [
                _("<b>%(name)s</b> — %(title)s")
                % {"name": other.username, "title": conversation.book.title},
                "",
            ]
            for item in conversation.messages.select_related("sender")[:20]:
                who = _("Siz") if item.sender_id == user.pk else item.sender.username
                lines.append(f"<b>{who}:</b> {item.text[:400]}")
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton(
                    _("✍️ Javob yozish"), callback_data=f"reply:{conversation.pk}"
                )
            )
            bot.send_message(call.message.chat.id, "\n".join(lines), reply_markup=markup)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("reply:"))
    @safe_handler
    def on_reply(call):
        user = callback_user(call)
        if not user:
            return
        conversation = (
            Conversation.objects.filter(pk=int(call.data.split(":")[1]))
            .filter(Q(buyer=user) | Q(seller=user))
            .first()
        )
        bot.answer_callback_query(call.id)
        if not conversation:
            return
        dialogs.start(call.message.chat.id, "message", "text", {"conversation": conversation.pk})
        with override(lang_of(user)):
            ask(call.message.chat.id, _("Javobingizni yozing:"))

    def send_payment_link(chat_id, user, payment):
        """To'lov havolasini yuboradi.

        Telegram tugmadagi manzil HTTPS bo'lishini talab qiladi, shuning
        uchun lokal ishlaganda (http) havola oddiy matn bo'lib yuboriladi.
        """
        link = payment_services.checkout_link(payment)
        text = _(
            "💳 <b>%(book)s</b>\n"
            "To'lash kerak: <b>%(amount)s so'm</b>\n"
            "Tizim: %(provider)s\n\n"
            "Havolani oching va to'lovni yakunlang — kitob shundan keyin "
            "o'zi kutubxonangizga tushadi."
        ) % {
            "book": payment.book.title,
            "amount": money(payment.amount),
            "provider": payment.get_provider_display(),
        }

        if link.startswith("https://"):
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(_("💳 To'lash"), url=link))
            bot.send_message(chat_id, text, reply_markup=markup)
            bot.send_message(chat_id, _("Menyu:"), reply_markup=main_keyboard(user))
        else:
            finish(chat_id, f"{text}\n\n{link}", user)

    def offer_book_payment(chat_id, user, book):
        """Kitobni to'lash uchun to'lov tizimini tanlashni taklif qiladi."""
        providers = payment_services.available_providers()
        if not providers:
            bot.send_message(chat_id, _("Hozircha to'lov tizimi sozlanmagan."))
            return

        markup = telebot.types.InlineKeyboardMarkup()
        for provider in providers:
            markup.add(
                telebot.types.InlineKeyboardButton(
                    provider.label, callback_data=f"bookpay:{book.pk}:{provider.value}"
                )
            )
        bot.send_message(
            chat_id,
            _(
                "<b>%(book)s</b>\n"
                "Narxi: <b>%(price)s so'm</b>\n\n"
                "To'lov tizimini tanlang (Uzcard · Humo · Visa · Mastercard):"
            )
            % {"book": book.title, "price": money(book.price)},
            reply_markup=markup,
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("bookpay:"))
    @safe_handler
    def on_book_payment(call):
        """Kitob uchun to'lov: buyurtma yaratiladi va havola beriladi."""
        user = callback_user(call)
        if not user:
            return
        bot.answer_callback_query(call.id)

        _prefix, book_id, provider = call.data.split(":", 2)
        book = Book.objects.filter(pk=int(book_id), is_active=True).first()
        chat_id = call.message.chat.id
        if not book:
            return

        with override(lang_of(user)):
            if Purchase.objects.filter(buyer=user, book=book).exists():
                bot.send_message(chat_id, _("Bu kitob sizda bor."))
                return
            try:
                payment = payment_services.create_payment(user, book, provider)
            except money_services.MoneyError as exc:
                finish(chat_id, str(exc), user)
                return
            payment.address = _("Telegram bot")
            payment.save(update_fields=["address"])
            send_payment_link(chat_id, user, payment)

    @bot.callback_query_handler(func=lambda c: c.data == "withdraw")
    @safe_handler
    def on_withdraw(call):
        user = callback_user(call)
        if not user:
            return
        bot.answer_callback_query(call.id)
        with override(lang_of(user)):
            if user.role != Role.SELLER:
                bot.send_message(call.message.chat.id, _("Bu faqat sotuvchilar uchun."))
                return
            dialogs.start(call.message.chat.id, "withdraw", "amount")
            ask(
                call.message.chat.id,
                _("Qancha yechasiz? (eng kam %(min)s so'm, balans %(balance)s so'm)")
                % {"min": money(settings.WITHDRAWAL_MIN), "balance": money(user.balance)},
            )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("lang:"))
    @safe_handler
    def on_language(call):
        user = callback_user(call)
        if not user:
            return
        code = call.data.split(":")[1]
        if code in dict(settings.LANGUAGES):
            user.language = code
            user.save(update_fields=["language"])
        with override(code):
            bot.answer_callback_query(call.id, _("Til o'zgartirildi"))
            bot.send_message(
                call.message.chat.id, _("Til o'zgartirildi."), reply_markup=main_keyboard(user)
            )

    @bot.callback_query_handler(func=lambda c: c.data == "notif")
    @safe_handler
    def on_notifications(call):
        user = callback_user(call)
        if not user:
            return
        link, _created = TelegramLink.objects.get_or_create(user=user)
        link.notifications = not link.notifications
        link.save(update_fields=["notifications"])
        with override(lang_of(user)):
            bot.answer_callback_query(
                call.id, _("Bildirishnoma yoqildi") if link.notifications else _("Bildirishnoma o'chirildi")
            )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("role:"))
    @safe_handler
    def on_role(call):
        user = callback_user(call)
        if not user:
            return
        role = call.data.split(":")[1]
        if role not in (Role.BUYER, Role.SELLER):
            bot.answer_callback_query(call.id)
            return
        user.role = role
        user.save(update_fields=["role"])
        with override(lang_of(user)):
            bot.answer_callback_query(call.id, _("Rol o'zgartirildi"))
            bot.send_message(
                call.message.chat.id,
                _("Yangi rol: <b>%(role)s</b>") % {"role": user.get_role_display()},
                reply_markup=main_keyboard(user),
            )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("buy:"))
    @safe_handler
    def on_buy(call):
        user = callback_user(call)
        if not user:
            return
        book = Book.objects.filter(pk=int(call.data.split(":")[1]), is_active=True).first()
        if not book:
            bot.answer_callback_query(call.id)
            return

        with override(lang_of(user)):
            if user.role != Role.BUYER:
                bot.answer_callback_query(
                    call.id, _("Sotib olish uchun xaridor rejimiga o'ting."), show_alert=True
                )
                return
            if Purchase.objects.filter(buyer=user, book=book).exists():
                bot.answer_callback_query(call.id, _("Bu kitob sizda bor."))
                return

            if book.seller_id == user.pk:
                bot.answer_callback_query(
                    call.id, _("O'z kitobingizni sotib ololmaysiz."), show_alert=True
                )
                return

            # Xaridorda hisob yo'q: kitob karta orqali to'lanadi. To'lov
            # tasdiqlangach kitob o'zi kutubxonaga tushadi.
            bot.answer_callback_query(call.id)
            offer_book_payment(call.message.chat.id, user, book)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("get:"))
    @safe_handler
    def on_get_file(call):
        user = user_for(call.message.chat.id)
        book = Book.objects.filter(pk=int(call.data.split(":")[1])).first()
        bot.answer_callback_query(call.id)
        if user and book:
            with override(lang_of(user)):
                send_file(call.message.chat.id, book, user)

    @bot.callback_query_handler(func=lambda c: c.data == "noop")
    @safe_handler
    def on_noop(call):
        bot.answer_callback_query(call.id)

    # ------------------------------------------------------------------
    # Qolgan matnlar qidiruv sifatida qabul qilinadi
    # ------------------------------------------------------------------

    @bot.message_handler(func=lambda m: True, content_types=["text"])
    @safe_handler
    def on_text(message):
        user = user_for(message.chat.id)
        if not user:
            send_welcome(message.chat.id)
            return
        with override(lang_of(user)):
            send_catalog(message.chat.id, 1, user, message.text.strip())
