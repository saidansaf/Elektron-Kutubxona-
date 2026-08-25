from decimal import Decimal

from django.conf import settings
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .storage import private_storage


def _cached_count(instance, relation):
    """Bog'lanish soni.

    `prefetch_related` bilan olingan bo'lsa xotiradagi ro'yxatdan
    sanaladi. Diqqat: `.count()` prefetch keshini ISHLATMAYDI — u har
    safar bazaga COUNT so'rovini yuboradi. Izohlar ro'yxatida bu har bir
    izoh uchun alohida so'rov degani edi.
    """
    cache = getattr(instance, "_prefetched_objects_cache", {})
    if relation in cache:
        return len(cache[relation])
    return getattr(instance, relation).count()


def _cached_liked_by(instance, relation, user):
    """Foydalanuvchi yoqtirganmi (prefetch bo'lsa bazaga bormaydi)."""
    if not user.is_authenticated:
        return False
    cache = getattr(instance, "_prefetched_objects_cache", {})
    if relation in cache:
        return any(like.user_id == user.pk for like in cache[relation])
    return getattr(instance, relation).filter(user=user).exists()


class BookQuerySet(models.QuerySet):
    """Kitob ro'yxatlari uchun umumiy so'rovlar."""

    def with_counts(self):
        """Reyting, sharh va yoqtirish sonini bitta so'rovda oladi.

        Busiz har bir kitob uchun uchta qo'shimcha so'rov ketardi —
        bosh sahifada 6 ta kitob 18 ta so'rov degani.

        Nega `annotate(Avg(...), Count(...))` emas, `Subquery`: bitta
        annotate ichida ikkita bog'lanish bo'yicha hisoblansa, SQL ularni
        bir-biriga ko'paytirib yuboradi va sonlar noto'g'ri chiqadi.
        Loyihada bu xato bir marta sotuvchi daromadida chiqqan (9 barobar
        ko'p ko'rsatgan), shuning uchun bu yerda ham xavfsiz yo'l tanlandi.
        """
        reviews = Review.objects.filter(book=models.OuterRef("pk")).values("book")
        likes = Like.objects.filter(book=models.OuterRef("pk")).values("book")

        def sub(queryset, expression, output):
            return models.Subquery(
                queryset.annotate(value=expression).values("value")[:1], output_field=output
            )

        return self.annotate(
            avg_rating=sub(reviews, models.Avg("rating"), models.FloatField()),
            reviews_total=Coalesce(
                sub(reviews, models.Count("id"), models.IntegerField()), 0
            ),
            likes_total=Coalesce(sub(likes, models.Count("id"), models.IntegerField()), 0),
        )


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Janr nomi"))

    class Meta:
        ordering = ["name"]
        verbose_name = _("Janr")
        verbose_name_plural = _("Janrlar")

    def __str__(self):
        return self.name


class Author(models.Model):
    full_name = models.CharField(max_length=150, verbose_name=_("Muallif to'liq ismi"))
    bio = models.TextField(blank=True, verbose_name=_("Muallif haqida"))
    birth_date = models.DateField(blank=True, null=True)
    photo = models.ImageField(upload_to="authors/", blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="authors_added"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = _("Muallif")
        verbose_name_plural = _("Mualliflar")

    def __str__(self):
        return self.full_name

    @property
    def books_count(self):
        return self.books.count()


class Book(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Kitob nomi"))
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name="books")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="books")
    language = models.CharField(max_length=5, choices=settings.BOOK_LANGUAGES, default="uz", verbose_name=_("Kitob tili"))
    pages = models.PositiveIntegerField(verbose_name=_("Sahifalar soni"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Narxi (so'm)"))
    description = models.TextField(blank=True, verbose_name=_("Tavsif"))
    cover = models.ImageField(upload_to="covers/", blank=True, null=True, verbose_name=_("Muqova"))
    file = models.FileField(
        upload_to="book_files/",
        storage=private_storage,
        blank=True,
        null=True,
        verbose_name=_("Kitob fayli (faqat PDF)"),
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )
    publish_year = models.PositiveIntegerField(blank=True, null=True, verbose_name=_("Nashr yili"))
    is_active = models.BooleanField(default=True, verbose_name=_("Sotuvda"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Kitob")
        verbose_name_plural = _("Kitoblar")

    objects = BookQuerySet.as_manager()

    def __str__(self):
        return f"{self.title} ({self.author})"

    def get_absolute_url(self):
        return reverse("books:detail", args=[self.pk])

    @property
    def average_rating(self):
        """O'rtacha baho (0 dan 5 gacha).

        `with_counts()` bilan olingan bo'lsa tayyor qiymat ishlatiladi.
        Aks holda bir marta hisoblanadi va obyektda saqlanadi — shablonda
        bu qiymat ikki joyda chiqadi va ilgari ikkita so'rov ketardi.
        """
        if hasattr(self, "avg_rating"):
            return round(self.avg_rating, 1) if self.avg_rating else 0
        if not hasattr(self, "_avg_cache"):
            agg = self.reviews.aggregate(avg=models.Avg("rating"))["avg"]
            self._avg_cache = round(agg, 1) if agg else 0
        return self._avg_cache

    @property
    def reviews_count(self):
        if hasattr(self, "reviews_total"):
            return self.reviews_total
        return _cached_count(self, "reviews")

    @property
    def likes_count(self):
        if hasattr(self, "likes_total"):
            return self.likes_total
        return _cached_count(self, "likes")

    def liked_by(self, user):
        return _cached_liked_by(self, "likes", user)

    def readable_by(self, user):
        """Kitob faylini ochishga haqli-yo'qligi.

        Sotuvchining o'zi, kitobni sotib olgan xaridor va administrator
        ochadi. Boshqalar uchun fayl umuman mavjud emasdek ko'rinadi.
        """
        if not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        if self.seller_id == user.pk:
            return True
        return self.purchases.filter(buyer=user).exists()


class Purchase(models.Model):
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchases")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="purchases")
    price_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    card_last4 = models.CharField(_("Karta oxirgi 4 raqami"), max_length=4, blank=True)
    address = models.CharField(_("Uy manzili"), max_length=255, blank=True)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchased_at"]
        unique_together = ("buyer", "book")
        verbose_name = _("Xarid")
        verbose_name_plural = _("Xaridlar")

    def __str__(self):
        return f"{self.buyer} -> {self.book}"


class ReadingProgress(models.Model):
    """Foydalanuvchi kitobni qayerigacha o'qigani.

    O'quvchi sahifani almashtirganda brauzer shu yozuvni yangilaydi, shuning
    uchun kitobni istalgan qurilmada to'xtagan joyidan davom ettirish mumkin.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reading_progress"
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reading_progress")
    page = models.PositiveIntegerField(_("Joriy sahifa"), default=1)
    total_pages = models.PositiveIntegerField(_("Jami sahifa"), default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ("user", "book")
        verbose_name = _("O'qish holati")
        verbose_name_plural = _("O'qish holatlari")

    def __str__(self):
        return f"{self.user} - {self.book} ({self.page}/{self.total_pages})"

    @property
    def percent(self):
        if not self.total_pages:
            return 0
        return min(100, round(self.page / self.total_pages * 100))

    @property
    def is_finished(self):
        return self.total_pages > 0 and self.page >= self.total_pages


class Wish(models.Model):
    """Istaklar ro'yxatiga qo'shilgan kitob.

    "Yoqtirish" (Like) - ommaviy baho, u kitob sahifasida hisoblanadi.
    "Istak" esa shaxsiy belgi: "keyin sotib olaman" degani va faqat
    egasiga ko'rinadi.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishes")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="wishes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "book")
        verbose_name = _("Istak")
        verbose_name_plural = _("Istaklar")

    def __str__(self):
        return f"{self.user} ★ {self.book}"


class Conversation(models.Model):
    """Xaridor va sotuvchi o'rtasidagi suhbat.

    Suhbat kitobga bog'lanadi: bir xaridor bir kitob bo'yicha bitta
    suhbat yuritadi, shunda savollar aralashib ketmaydi.
    """

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="conversations")
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_as_buyer"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_as_seller"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ("book", "buyer")
        verbose_name = _("Suhbat")
        verbose_name_plural = _("Suhbatlar")

    def __str__(self):
        return f"{self.buyer} ↔ {self.seller} ({self.book})"

    def other_side(self, user):
        """Suhbatdagi ikkinchi tomon."""
        return self.seller if user.pk == self.buyer_id else self.buyer

    def unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    """Suhbatdagi bitta xabar."""

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    text = models.TextField(_("Xabar"))
    is_read = models.BooleanField(_("O'qilgan"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Xabar")
        verbose_name_plural = _("Xabarlar")

    def __str__(self):
        return f"{self.sender}: {self.text[:40]}"


class Like(models.Model):
    """Foydalanuvchining kitobni yoqtirishi."""

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("book", "user")
        verbose_name = _("Yoqtirish")
        verbose_name_plural = _("Yoqtirishlar")

    def __str__(self):
        return f"{self.user} ❤ {self.book}"


class Review(models.Model):
    """Kitobga qoldirilgan baho va izoh.

    Sotib olish shart emas - istalgan ro'yxatdan o'tgan foydalanuvchi
    yoqtirishi, baholashi va izoh yozishi mumkin.
    """

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("book", "buyer")
        verbose_name = _("Sharh")
        verbose_name_plural = _("Sharhlar")

    def __str__(self):
        return f"{self.buyer} - {self.book} ({self.rating}*)"

    @property
    def likes_count(self):
        return _cached_count(self, "likes")

    def liked_by(self, user):
        return _cached_liked_by(self, "likes", user)


class ReviewLike(models.Model):
    """Izohga bosilgan yoqtirish."""

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("review", "user")
        verbose_name = _("Izoh yoqtirishi")
        verbose_name_plural = _("Izoh yoqtirishlari")


class Reply(models.Model):
    """Izohga javob.

    Faqat bitta daraja: javobga javob yozib bo'lmaydi.
    """

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="replies")
    text = models.TextField(_("Javob"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Javob")
        verbose_name_plural = _("Javoblar")

    def __str__(self):
        return f"{self.author} -> {self.review_id}"

    @property
    def likes_count(self):
        return _cached_count(self, "likes")

    def liked_by(self, user):
        return _cached_liked_by(self, "likes", user)


class ReplyLike(models.Model):
    """Javobga bosilgan yoqtirish."""

    reply = models.ForeignKey(Reply, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reply_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("reply", "user")
        verbose_name = _("Javob yoqtirishi")
        verbose_name_plural = _("Javob yoqtirishlari")
