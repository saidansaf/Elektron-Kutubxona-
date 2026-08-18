"""Telegram bot testlari — haqiqiy Telegram'siz.

Bot handlerlari oddiy funksiyalar: ular `telebot`ning `bot` obyektiga
xabar yuboradi. Shu obyektni soxta (fake) nusxa bilan almashtirsak,
butun oqimni tarmoqqa chiqmasdan tekshirish mumkin.

Asosiy tekshiruv: **bot va sayt bitta bazada ishlaydi.** Botda kitob
qo'shilsa, u saytdagi so'rovlarda ham chiqishi kerak.
"""

import re
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, TelegramLink, Withdrawal
from apps.books.models import Author, Book, Conversation, Genre, Like, Review, Wish

User = get_user_model()


class FakeBot:
    """telebot.TeleBot o'rniga: handlerlarni yig'adi, javoblarni saqlaydi."""

    def __init__(self):
        self.messages = []          # (chat_id, matn)
        self.documents = []
        self.message_handlers = []  # (tekshiruvchi, funksiya)
        self.callback_handlers = []
        self.answered = []
        self.deleted = []
        self.files = {}             # file_id -> baytlar

    # --- telebot API'sining biz ishlatadigan qismi ---

    def middleware_handler(self, update_types=None):
        return lambda func: func

    def message_handler(self, commands=None, regexp=None, func=None, content_types=None):
        types = content_types or ["text"]

        def decorator(handler):
            def check(message):
                if message.content_type not in types:
                    return False
                text = message.text or ""
                if commands is not None:
                    return text.startswith("/") and text[1:].split()[0].split("@")[0] in commands
                if regexp is not None:
                    return bool(re.match(regexp, text))
                if func is not None:
                    return bool(func(message))
                return False

            self.message_handlers.append((check, handler))
            return handler

        return decorator

    def callback_query_handler(self, func=None):
        def decorator(handler):
            self.callback_handlers.append((func, handler))
            return handler

        return decorator

    def send_message(self, chat_id, text, reply_markup=None, **kwargs):
        self.messages.append((chat_id, text))

    def send_photo(self, chat_id, photo, caption="", reply_markup=None, **kwargs):
        self.messages.append((chat_id, caption))

    def send_document(self, chat_id, document, caption="", **kwargs):
        self.documents.append(caption)
        self.messages.append((chat_id, caption or "[fayl]"))

    def answer_callback_query(self, callback_id, text="", **kwargs):
        self.answered.append(text)

    def edit_message_reply_markup(self, chat_id=None, message_id=None, reply_markup=None):
        pass

    def edit_message_text(self, text, chat_id=None, message_id=None, **kwargs):
        self.messages.append((chat_id, text))

    def delete_message(self, chat_id, message_id):
        self.deleted.append(message_id)

    def get_file(self, file_id):
        return SimpleNamespace(file_path=file_id)

    def download_file(self, path):
        return self.files.get(path, b"%PDF-1.4 sinov")

    # --- test yordamchilari ---

    def _message(self, chat_id, text=None, content_type="text", **extra):
        message = SimpleNamespace(
            text=text,
            content_type=content_type,
            chat=SimpleNamespace(id=chat_id),
            message_id=len(self.messages) + 1,
            from_user=SimpleNamespace(id=chat_id, username="tguser", first_name="T"),
            photo=None,
            document=None,
        )
        for key, value in extra.items():
            setattr(message, key, value)
        return message

    def deliver(self, chat_id, text):
        """Foydalanuvchi xabar yuborgandek qiladi. Birinchi mos handler ishlaydi."""
        return self._dispatch(self._message(chat_id, text))

    def send_photo_from_user(self, chat_id, file_id="photo-1"):
        message = self._message(
            chat_id, content_type="photo", photo=[SimpleNamespace(file_id=file_id)]
        )
        return self._dispatch(message)

    def send_document_from_user(self, chat_id, name="kitob.pdf", file_id="doc-1", size=1000):
        message = self._message(
            chat_id,
            content_type="document",
            document=SimpleNamespace(file_name=name, file_id=file_id, file_size=size),
        )
        return self._dispatch(message)

    def _dispatch(self, message):
        for check, handler in self.message_handlers:
            if check(message):
                handler(message)
                return handler.__name__
        return None

    def press(self, chat_id, data):
        """Inline tugma bosilgandek qiladi."""
        call = SimpleNamespace(
            id="cb1",
            data=data,
            message=SimpleNamespace(chat=SimpleNamespace(id=chat_id), message_id=1),
            from_user=SimpleNamespace(id=chat_id, username="tguser", first_name="T"),
        )
        for check, handler in self.callback_handlers:
            if check(call):
                handler(call)
                return handler.__name__
        return None

    @property
    def last(self):
        return self.messages[-1][1] if self.messages else ""

    def said(self, needle):
        return any(needle in text for _chat, text in self.messages)


class BotTestCase(TestCase):
    """Umumiy tayyorgarlik: sotuvchi, xaridor, kitob va soxta bot."""

    CHAT = 555001

    def setUp(self):
        from apps.core.botlib.handlers import register_handlers

        self.seller = User.objects.create_user(
            username="sotuvchi", password="Parol-12345", role=Role.SELLER
        )
        self.buyer = User.objects.create_user(
            username="xaridor", password="Parol-12345", role=Role.BUYER, balance=Decimal("500000")
        )
        self.author = Author.objects.create(full_name="Abdulla Qodiriy")
        self.book = Book.objects.create(
            title="Otkan kunlar",
            author=self.author,
            seller=self.seller,
            pages=100,
            price=Decimal("45000"),
            language="uz",
        )

        self.bot = FakeBot()
        register_handlers(self.bot)

    def link(self, user=None, chat_id=None):
        TelegramLink.objects.create(
            user=user or self.buyer, chat_id=chat_id or self.CHAT, linked_at=timezone.now()
        )


class LinkTests(BotTestCase):
    """Hisobni ulash: kod bilan ham, login/parol bilan ham."""

    def test_start_ulanmaganga_korsatma_beradi(self):
        self.bot.deliver(self.CHAT, "/start")
        self.assertIn("/kirish", self.bot.last)

    def test_togri_kod_hisobni_ulaydi(self):
        TelegramLink.objects.create(
            user=self.buyer, code="123456", code_created_at=timezone.now()
        )
        self.bot.deliver(self.CHAT, "123456")

        link = TelegramLink.objects.get(user=self.buyer)
        self.assertEqual(link.chat_id, self.CHAT)
        self.assertIn(self.buyer.username, self.bot.last)

    def test_notogri_kod_rad_etiladi(self):
        TelegramLink.objects.create(user=self.buyer, code="111111", code_created_at=timezone.now())
        self.bot.deliver(self.CHAT, "999999")
        self.assertIn("noto'g'ri", self.bot.last)
        self.assertFalse(TelegramLink.objects.filter(chat_id=self.CHAT).exists())

    def test_eskirgan_kod_ishlamaydi(self):
        TelegramLink.objects.create(
            user=self.buyer, code="123456", code_created_at=timezone.now() - timedelta(hours=2)
        )
        self.bot.deliver(self.CHAT, "123456")
        self.assertIn("muddati", self.bot.last)

    def test_login_va_parol_bilan_kirish(self):
        self.bot.deliver(self.CHAT, "/kirish")
        self.bot.deliver(self.CHAT, "xaridor")
        self.bot.deliver(self.CHAT, "Parol-12345")

        link = TelegramLink.objects.get(user=self.buyer)
        self.assertEqual(link.chat_id, self.CHAT)
        self.assertIn("Xush kelibsiz", self.bot.last)

    def test_notogri_parol_kiritmaydi(self):
        self.bot.deliver(self.CHAT, "/kirish")
        self.bot.deliver(self.CHAT, "xaridor")
        self.bot.deliver(self.CHAT, "boshqa-parol")

        self.assertFalse(TelegramLink.objects.filter(chat_id=self.CHAT).exists())
        self.assertIn("noto'g'ri", self.bot.last)

    def test_parol_yozilgan_xabar_ochiriladi(self):
        """Parol Telegram tarixida qolib ketmasligi kerak."""
        self.bot.deliver(self.CHAT, "/kirish")
        self.bot.deliver(self.CHAT, "xaridor")
        self.bot.deliver(self.CHAT, "Parol-12345")
        self.assertEqual(len(self.bot.deleted), 1)

    def test_chiqish_ulanishni_uzadi(self):
        self.link()
        self.bot.deliver(self.CHAT, "/chiqish")
        link = TelegramLink.objects.get(user=self.buyer)
        self.assertIsNone(link.chat_id)


class CatalogTests(BotTestCase):
    def test_katalog_kitoblarni_korsatadi(self):
        self.link()
        self.bot.deliver(self.CHAT, "📚 Katalog")
        self.assertIn("Otkan kunlar", self.bot.last)

    def test_qidiruv_topadi(self):
        self.link()
        Book.objects.create(
            title="Mehrobdan chayon", author=self.author, seller=self.seller,
            pages=80, price=Decimal("62000"),
        )
        self.bot.deliver(self.CHAT, "🔍 Qidiruv")
        self.bot.deliver(self.CHAT, "Otkan")

        self.assertIn("Otkan kunlar", self.bot.last)
        self.assertNotIn("Mehrobdan", self.bot.last)

    def test_balans_korinadi(self):
        self.link()
        self.bot.deliver(self.CHAT, "💰 Balans")
        self.assertIn("500 000", self.bot.last)

    def test_istaklar_royxati(self):
        self.link()
        Wish.objects.create(user=self.buyer, book=self.book)
        self.bot.deliver(self.CHAT, "⭐ Istaklarim")
        self.assertIn("Otkan kunlar", self.bot.last)


class PurchaseTests(BotTestCase):
    def test_bot_orqali_sotib_olish_balansdan_yechadi(self):
        self.link()
        self.bot.press(self.CHAT, f"buy:{self.book.pk}")

        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.balance, Decimal("455000"))
        self.assertTrue(self.buyer.purchases.filter(book=self.book).exists())

    def test_mablag_yetmasa_xarid_bolmaydi(self):
        self.buyer.balance = Decimal("100")
        self.buyer.save(update_fields=["balance"])
        self.link()

        self.bot.press(self.CHAT, f"buy:{self.book.pk}")
        self.assertFalse(self.buyer.purchases.filter(book=self.book).exists())

    def test_ulanmagan_chat_xarid_qila_olmaydi(self):
        self.bot.press(self.CHAT, f"buy:{self.book.pk}")
        self.assertEqual(self.book.purchases.count(), 0)


class SellerBookTests(BotTestCase):
    """Sotuvchi botdan kitob qo'shadi va boshqaradi."""

    def setUp(self):
        super().setUp()
        self.link(self.seller)

    def add_book(self, with_file=True):
        steps = [
            "➕ Kitob qo'shish",
            "Yangi kitob",
            "Yangi Muallif",
            "Ilmiy",
            "O'zbekcha",
            "250",
            "75000",
            "Qisqacha tavsif",
        ]
        for step in steps:
            self.bot.deliver(self.CHAT, step)
        self.bot.deliver(self.CHAT, "⏭ O'tkazib yuborish")  # muqova
        if with_file:
            self.bot.send_document_from_user(self.CHAT)
        else:
            self.bot.deliver(self.CHAT, "⏭ O'tkazib yuborish")

    def test_botdan_qoshilgan_kitob_bazaga_tushadi(self):
        self.add_book()

        book = Book.objects.get(title="Yangi kitob")
        self.assertEqual(book.seller, self.seller)
        self.assertEqual(book.price, Decimal("75000"))
        self.assertEqual(book.pages, 250)
        self.assertEqual(book.language, "uz")
        self.assertEqual(book.author.full_name, "Yangi Muallif")
        self.assertEqual(book.genre.name, "Ilmiy")
        self.assertTrue(book.file)

    def test_botdan_qoshilgan_kitob_saytda_korinadi(self):
        """Eng muhim tekshiruv: bot va sayt bitta bazada ishlaydi."""
        self.add_book()

        response = self.client.get(reverse("books:catalog"))
        self.assertContains(response, "Yangi kitob")

    def test_mavjud_muallif_takrorlanmaydi(self):
        for step in ["➕ Kitob qo'shish", "Ikkinchi kitob", "Abdulla Qodiriy", "Ilmiy",
                     "O'zbekcha", "100", "50000", "Tavsif"]:
            self.bot.deliver(self.CHAT, step)
        self.bot.deliver(self.CHAT, "⏭ O'tkazib yuborish")
        self.bot.deliver(self.CHAT, "⏭ O'tkazib yuborish")

        self.assertEqual(Author.objects.filter(full_name="Abdulla Qodiriy").count(), 1)

    def test_notogri_narx_qayta_soraladi(self):
        for step in ["➕ Kitob qo'shish", "Kitob", "Muallif", "Ilmiy", "O'zbekcha", "100"]:
            self.bot.deliver(self.CHAT, step)
        self.bot.deliver(self.CHAT, "arzon")

        self.assertIn("raqam", self.bot.last)
        self.assertFalse(Book.objects.filter(title="Kitob").exists())

    def test_pdf_bolmagan_fayl_qabul_qilinmaydi(self):
        for step in ["➕ Kitob qo'shish", "Kitob", "Muallif", "Ilmiy", "O'zbekcha",
                     "100", "50000", "Tavsif"]:
            self.bot.deliver(self.CHAT, step)
        self.bot.deliver(self.CHAT, "⏭ O'tkazib yuborish")
        self.bot.send_document_from_user(self.CHAT, name="kitob.docx")

        self.assertIn("PDF", self.bot.last)
        self.assertFalse(Book.objects.filter(title="Kitob").exists())

    def test_bekor_qilish_kitobni_saqlamaydi(self):
        self.bot.deliver(self.CHAT, "➕ Kitob qo'shish")
        self.bot.deliver(self.CHAT, "Bekor bo'ladigan kitob")
        self.bot.deliver(self.CHAT, "❌ Bekor qilish")

        self.assertFalse(Book.objects.filter(title="Bekor bo'ladigan kitob").exists())
        self.assertIn("Bekor qilindi", self.bot.last)

    def test_xaridor_kitob_qosha_olmaydi(self):
        TelegramLink.objects.filter(chat_id=self.CHAT).delete()
        self.link(self.buyer)
        self.bot.deliver(self.CHAT, "➕ Kitob qo'shish")
        self.assertIn("sotuvchi", self.bot.last)

    def test_narxni_ozgartirish(self):
        self.bot.press(self.CHAT, f"price:{self.book.pk}")
        self.bot.deliver(self.CHAT, "99000")

        self.book.refresh_from_db()
        self.assertEqual(self.book.price, Decimal("99000"))

    def test_sotuvdan_olish(self):
        self.bot.press(self.CHAT, f"toggle:{self.book.pk}")
        self.book.refresh_from_db()
        self.assertFalse(self.book.is_active)

    def test_kitobni_ochirish(self):
        self.bot.press(self.CHAT, f"delok:{self.book.pk}")
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())

    def test_boshqaning_kitobini_ozgartirib_bolmaydi(self):
        other = User.objects.create_user(username="begona", password="x", role=Role.SELLER)
        foreign = Book.objects.create(
            title="Begona kitob", author=self.author, seller=other,
            pages=10, price=Decimal("1000"),
        )
        self.bot.press(self.CHAT, f"delok:{foreign.pk}")
        self.assertTrue(Book.objects.filter(pk=foreign.pk).exists())


class ReviewTests(BotTestCase):
    def setUp(self):
        super().setUp()
        self.link()

    def test_baho_va_izoh_saqlanadi(self):
        self.bot.press(self.CHAT, f"star:{self.book.pk}:5")
        self.bot.deliver(self.CHAT, "Juda zo'r kitob")

        review = Review.objects.get(book=self.book, buyer=self.buyer)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "Juda zo'r kitob")

    def test_izohsiz_baho_ham_saqlanadi(self):
        self.bot.press(self.CHAT, f"star:{self.book.pk}:4")
        self.bot.deliver(self.CHAT, "⏭ O'tkazib yuborish")

        review = Review.objects.get(book=self.book, buyer=self.buyer)
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, "")

    def test_botdagi_sharh_saytda_korinadi(self):
        self.bot.press(self.CHAT, f"star:{self.book.pk}:5")
        self.bot.deliver(self.CHAT, "Botdan yozilgan sharh")

        response = self.client.get(reverse("books:detail", args=[self.book.pk]))
        self.assertContains(response, "Botdan yozilgan sharh")

    def test_yoqtirish(self):
        self.bot.press(self.CHAT, f"like:{self.book.pk}")
        self.assertTrue(Like.objects.filter(user=self.buyer, book=self.book).exists())

        self.bot.press(self.CHAT, f"like:{self.book.pk}")
        self.assertFalse(Like.objects.filter(user=self.buyer, book=self.book).exists())

    def test_istaklarga_qoshish(self):
        self.bot.press(self.CHAT, f"wish:{self.book.pk}")
        self.assertTrue(Wish.objects.filter(user=self.buyer, book=self.book).exists())


class MessageTests(BotTestCase):
    def setUp(self):
        super().setUp()
        self.link()

    def test_sotuvchiga_savol_yuborish(self):
        self.bot.press(self.CHAT, f"ask:{self.book.pk}")
        self.bot.deliver(self.CHAT, "Bu kitob nechta betdan iborat?")

        conversation = Conversation.objects.get(book=self.book, buyer=self.buyer)
        self.assertEqual(conversation.seller, self.seller)
        self.assertEqual(conversation.messages.count(), 1)
        self.assertEqual(conversation.messages.first().sender, self.buyer)

    def test_botdagi_xabar_saytda_korinadi(self):
        self.bot.press(self.CHAT, f"ask:{self.book.pk}")
        self.bot.deliver(self.CHAT, "Botdan yozilgan savol")

        self.client.force_login(self.seller)
        conversation = Conversation.objects.get(book=self.book)
        response = self.client.get(reverse("books:conversation", args=[conversation.pk]))
        self.assertContains(response, "Botdan yozilgan savol")

    def test_suhbatlar_royxati(self):
        conversation = Conversation.objects.create(
            book=self.book, buyer=self.buyer, seller=self.seller
        )
        conversation.messages.create(sender=self.seller, text="Salom")
        self.bot.deliver(self.CHAT, "💬 Xabarlar")
        self.assertIn(self.seller.username, self.bot.last)

    def test_suhbat_ochilganda_oqilgan_deb_belgilanadi(self):
        conversation = Conversation.objects.create(
            book=self.book, buyer=self.buyer, seller=self.seller
        )
        conversation.messages.create(sender=self.seller, text="Javob")

        self.bot.press(self.CHAT, f"conv:{conversation.pk}")
        self.assertEqual(conversation.unread_count(self.buyer), 0)

    def test_begona_suhbatni_ocha_olmaydi(self):
        other = User.objects.create_user(username="begona2", password="x", role=Role.BUYER)
        conversation = Conversation.objects.create(
            book=self.book, buyer=other, seller=self.seller
        )
        conversation.messages.create(sender=other, text="Maxfiy savol")

        self.bot.press(self.CHAT, f"conv:{conversation.pk}")
        self.assertFalse(self.bot.said("Maxfiy savol"))


class MoneyTests(BotTestCase):
    def test_botdan_hisobni_toldirish(self):
        self.link()
        self.bot.press(self.CHAT, "topup")
        self.bot.deliver(self.CHAT, "50000")
        self.bot.deliver(self.CHAT, "8600123456789012")

        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.balance, Decimal("550000"))
        self.assertEqual(self.buyer.topups.count(), 1)

    def test_juda_kichik_summa_qabul_qilinmaydi(self):
        self.link()
        self.bot.press(self.CHAT, "topup")
        self.bot.deliver(self.CHAT, "10")
        self.bot.deliver(self.CHAT, "8600123456789012")

        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.balance, Decimal("500000"))

    def test_notogri_karta_qabul_qilinmaydi(self):
        self.link()
        self.bot.press(self.CHAT, "topup")
        self.bot.deliver(self.CHAT, "50000")
        self.bot.deliver(self.CHAT, "8600")

        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.balance, Decimal("500000"))
        self.assertIn("16", self.bot.last)

    def test_botdan_pul_yechish(self):
        self.seller.balance = Decimal("300000")
        self.seller.save(update_fields=["balance"])
        self.link(self.seller)

        self.bot.press(self.CHAT, "withdraw")
        self.bot.deliver(self.CHAT, "100000")
        self.bot.deliver(self.CHAT, "8600123456789012")

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.balance, Decimal("200000"))
        self.assertEqual(Withdrawal.objects.filter(seller=self.seller).count(), 1)

    def test_balansdan_kop_yechib_bolmaydi(self):
        self.seller.balance = Decimal("50000")
        self.seller.save(update_fields=["balance"])
        self.link(self.seller)

        self.bot.press(self.CHAT, "withdraw")
        self.bot.deliver(self.CHAT, "900000")
        self.bot.deliver(self.CHAT, "8600123456789012")

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.balance, Decimal("50000"))
        self.assertFalse(Withdrawal.objects.exists())

    def test_xaridor_pul_yecha_olmaydi(self):
        self.link()
        self.bot.press(self.CHAT, "withdraw")
        self.assertIn("sotuvchilar", self.bot.last)


class SettingsTests(BotTestCase):
    def setUp(self):
        super().setUp()
        self.link()

    def test_tilni_ozgartirish(self):
        self.bot.press(self.CHAT, "lang:ru")
        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.language, "ru")

    def test_bildirishnomani_ochirish(self):
        self.bot.press(self.CHAT, "notif")
        link = TelegramLink.objects.get(user=self.buyer)
        self.assertFalse(link.notifications)

    def test_rolni_almashtirish(self):
        self.bot.press(self.CHAT, f"role:{Role.SELLER}")
        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.role, Role.SELLER)

    def test_sozlamalar_korinadi(self):
        self.bot.deliver(self.CHAT, "⚙️ Sozlamalar")
        self.assertIn(self.buyer.username, self.bot.last)


class RegistrationTests(BotTestCase):
    """Handlerlar ro'yxatdan o'tganini tekshiradi.

    Dekoratorlar tartibi buzilsa handlerlar jimgina yo'qoladi — bot
    hech qanday xato bermay javob berishni to'xtatadi.
    """

    def test_barcha_handlerlar_royxatdan_otadi(self):
        self.assertGreaterEqual(len(self.bot.message_handlers), 14)
        self.assertGreaterEqual(len(self.bot.callback_handlers), 18)

    def test_notanish_matn_qidiruvga_tushadi(self):
        self.link()
        self.bot.deliver(self.CHAT, "Otkan")
        self.assertIn("Otkan kunlar", self.bot.last)


class TranslationTests(BotTestCase):
    """Bot uch tilda gapiradi: matn foydalanuvchi tiliga qarab tanlanadi."""

    def test_menyu_rus_tilida(self):
        self.buyer.language = "ru"
        self.buyer.save(update_fields=["language"])
        self.link()

        self.bot.deliver(self.CHAT, "/start")
        self.assertIn("Здравствуйте", self.bot.last)

    def test_menyu_ingliz_tilida(self):
        self.buyer.language = "en"
        self.buyer.save(update_fields=["language"])
        self.link()

        self.bot.deliver(self.CHAT, "/start")
        self.assertIn("Hello", self.bot.last)

    def test_tugmalar_uch_tilda_ham_tushuniladi(self):
        """Foydalanuvchi tilni almashtirsa, eski tugma ham ishlashi kerak."""
        self.buyer.language = "ru"
        self.buyer.save(update_fields=["language"])
        self.link()

        # Klaviaturada eski o'zbekcha yozuv qolgan bo'lishi mumkin
        self.bot.deliver(self.CHAT, "📚 Katalog")
        self.assertIn("Otkan kunlar", self.bot.last)


class RoleSelectionTests(BotTestCase):
    """Roli tanlanmagan hisob (masalan administrator) botda tiqilib qolmasin.

    Menyu rolga qarab tuziladi. Rol "none" bo'lsa "Kitob qo'shish" ham,
    "Kutubxonam" ham ko'rinmaydi — shuning uchun bot rolni o'zi so'rashi
    va ikkala variantni ham taklif qilishi kerak.
    """

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(username="admin1", password="x")
        self.admin.role = Role.NONE
        self.admin.save(update_fields=["role"])
        self.link(self.admin)

    def test_start_rol_tanlashni_taklif_qiladi(self):
        self.bot.deliver(self.CHAT, "/start")
        self.assertTrue(self.bot.said("Rolingiz hali tanlanmagan"))

    def test_ikkala_rol_ham_taklif_qilinadi(self):
        """Ilgari faqat bittasi ko'rsatilardi va sotuvchiga o'tib bo'lmasdi."""
        self.bot.deliver(self.CHAT, "/start")
        self.bot.press(self.CHAT, f"role:{Role.SELLER}")

        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, Role.SELLER)

    def test_sotuvchi_bolgach_kitob_qosha_oladi(self):
        self.bot.press(self.CHAT, f"role:{Role.SELLER}")
        self.bot.deliver(self.CHAT, "➕ Kitob qo'shish")
        self.assertIn("Kitob nomini", self.bot.last)

    def test_sozlamalarda_ikkala_rol_tugmasi_bor(self):
        self.bot.deliver(self.CHAT, "⚙️ Sozlamalar")
        # Roli yo'q hisobga ikkala rol ham taklif qilinishi kerak
        self.bot.press(self.CHAT, f"role:{Role.BUYER}")
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, Role.BUYER)
