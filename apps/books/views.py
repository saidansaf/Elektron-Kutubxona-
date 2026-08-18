import json
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import (
    Avg,
    Count,
    DecimalField,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, TruncDate
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.core import telegram
from apps.core.decorators import buyer_required, seller_required

from .forms import (
    DEFAULT_SORT,
    SORT_OPTIONS,
    AuthorForm,
    BookFilterForm,
    BookForm,
    CheckoutForm,
    GenreForm,
    ReplyForm,
    ReviewForm,
)
from .models import (
    Author,
    Book,
    Conversation,
    Genre,
    Like,
    Message,
    ReadingProgress,
    Reply,
    ReplyLike,
    Purchase,
    Review,
    ReviewLike,
    Wish,
)
from .services import PurchaseError, purchase_book
from .storage import private_storage


#: Katalog keshi qaysi parametrlarga bog'liq
CATALOG_FILTERS = ("q", "language", "genre", "author", "min_price", "max_price", "sort")


def _catalog_cache_key(request, page_number):
    """Filtrlardan barqaror kalit yasaydi.

    Parametrlar tartibi va ortiqcha probellar kalitga ta'sir qilmasligi
    kerak: `?q=abc&language=uz` va `?language=uz&q=abc` bir xil natija
    beradi, demak keshda ham bitta yozuv bo'lishi kerak.
    """
    parts = [f"{name}={(request.GET.get(name) or '').strip()}" for name in CATALOG_FILTERS]
    parts.append(f"page={page_number}")
    return "|".join(parts)


def catalog_view(request):
    books = Book.objects.filter(is_active=True).select_related("author", "genre", "seller")
    filter_form = BookFilterForm(request.GET or None)

    sort = DEFAULT_SORT
    if filter_form.is_valid():
        data = filter_form.cleaned_data
        if data.get("q"):
            books = books.filter(
                Q(title__icontains=data["q"]) | Q(author__full_name__icontains=data["q"])
            )
        if data.get("language"):
            books = books.filter(language=data["language"])
        if data.get("genre"):
            books = books.filter(genre=data["genre"])
        if data.get("author"):
            books = books.filter(author=data["author"])
        if data.get("min_price") is not None:
            books = books.filter(price__gte=data["min_price"])
        if data.get("max_price") is not None:
            books = books.filter(price__lte=data["max_price"])
        sort = data.get("sort") or DEFAULT_SORT

    # Reyting va sotuvlar soni bo'yicha saralash uchun ular hisoblanishi kerak.
    # Ikkalasini bitta `annotate` da hisoblab bo'lmaydi - sharhlar va xaridlar
    # bir-biriga ko'payib ketadi, shuning uchun `distinct=True` ishlatiladi.
    books = books.annotate(
        avg_rating=Avg("reviews__rating"),
        sales_total=Count("purchases", distinct=True),
    ).order_by(*SORT_OPTIONS[sort][1])

    paginator = Paginator(books, 9)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "books/catalog.html",
        {
            "page_obj": page_obj,
            "filter_form": filter_form,
            # Keshlangan natijalar ro'yxatini filtrga bog'laydigan kalit
            "catalog_key": _catalog_cache_key(request, page_obj.number),
            "cache_timeout_catalog": settings.CACHE_TIMEOUT_CATALOG,
        },
    )


def book_detail_view(request, pk):
    book = get_object_or_404(Book.objects.select_related("author", "genre", "seller"), pk=pk)
    reviews = (
        book.reviews.select_related("buyer")
        .prefetch_related("replies__author", "likes", "replies__likes")
        .all()
    )

    has_purchased = False
    my_review = None
    wished = False
    conversation = None
    if request.user.is_authenticated:
        has_purchased = Purchase.objects.filter(buyer=request.user, book=book).exists()
        my_review = Review.objects.filter(buyer=request.user, book=book).first()
        wished = Wish.objects.filter(user=request.user, book=book).exists()
        conversation = Conversation.objects.filter(book=book, buyer=request.user).first()

    # Baholash va izoh yozish uchun sotib olish shart emas - kirgan bo'lishi kifoya.
    review_form = ReviewForm(instance=my_review) if request.user.is_authenticated else None

    return render(
        request,
        "books/detail.html",
        {
            "book": book,
            "reviews": reviews,
            "has_purchased": has_purchased,
            "my_review": my_review,
            "wished": wished,
            "conversation": conversation,
            "review_form": review_form,
            "reply_form": ReplyForm() if request.user.is_authenticated else None,
        },
    )


def _book_for_reading(request, pk):
    """Faylni ochishga haqli bo'lsagina kitobni qaytaradi.

    Haqi bo'lmasa 404 beriladi (403 emas): begona odam kitobning fayli
    umuman bor-yo'qligini ham bilmasligi kerak.
    """
    book = get_object_or_404(Book.objects.select_related("author", "seller"), pk=pk)
    if not book.file or not book.readable_by(request.user):
        raise Http404
    return book


def _serve(book, as_attachment):
    try:
        handle = book.file.open("rb")
    except FileNotFoundError as exc:
        raise Http404 from exc
    filename = f"{book.title}.pdf".replace("/", "-")
    return FileResponse(
        handle, as_attachment=as_attachment, filename=filename, content_type="application/pdf"
    )


@login_required
def book_file_view(request, pk):
    """PDF ni brauzer ichida ochish uchun uzatadi (o'quvchi shu manzildan oladi)."""
    return _serve(_book_for_reading(request, pk), as_attachment=False)


@login_required
def book_download_view(request, pk):
    """PDF ni faylga saqlash uchun uzatadi."""
    return _serve(_book_for_reading(request, pk), as_attachment=True)


@staff_member_required
def private_file_view(request, path):
    """`FieldFile.url` uchun zaxira yo'l.

    Django admin panelida kitob sahifasi ochilganda faylga havola chiziladi.
    Havola shu yerga tushadi va faqat xodimlar uchun ochiq - oddiy
    foydalanuvchi bu manzilni bilsa ham hech narsa ololmaydi.
    """
    storage = private_storage()
    if not storage.exists(path):
        raise Http404
    return FileResponse(storage.open(path, "rb"), content_type="application/pdf")


@login_required
def book_read_view(request, pk):
    """Kitobni brauzerda o'qish sahifasi."""
    book = _book_for_reading(request, pk)
    progress = ReadingProgress.objects.filter(user=request.user, book=book).first()
    return render(
        request,
        "books/read.html",
        {"book": book, "start_page": progress.page if progress else 1},
    )


@login_required
@require_POST
def reading_progress_view(request, pk):
    """O'quvchi sahifani almashtirganda joriy sahifani saqlaydi."""
    book = _book_for_reading(request, pk)
    try:
        payload = json.loads(request.body or "{}")
        page = int(payload.get("page", 1))
        total = int(payload.get("total", 0))
    except (ValueError, TypeError):
        return JsonResponse({"ok": False}, status=400)

    total = max(0, total)
    page = max(1, min(page, total) if total else page)

    ReadingProgress.objects.update_or_create(
        user=request.user, book=book, defaults={"page": page, "total_pages": total}
    )
    return JsonResponse({"ok": True, "page": page, "total": total})


@buyer_required
def buy_book_view(request, pk):
    """Sotib olish sahifasi: buyurtma xulosasi, karta to'lovi, yoqtirish va izohlar."""
    book = get_object_or_404(
        Book.objects.select_related("author", "genre", "seller"), pk=pk, is_active=True
    )
    buyer = request.user

    if Purchase.objects.filter(buyer=buyer, book=book).exists():
        messages.info(request, _("Siz bu kitobni allaqachon sotib olgansiz."))
        return redirect("books:detail", pk=pk)

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            card_number = form.cleaned_data["card_number"]
            try:
                # Pul harakati sayt va bot uchun bitta joyda (services.py)
                purchase = purchase_book(
                    buyer,
                    book,
                    card_last4=card_number[-4:],
                    address=form.cleaned_data["address"],
                )
            except PurchaseError as exc:
                messages.error(request, str(exc))
            else:
                telegram.notify_sale(purchase)
                messages.success(request, _("Kitob muvaffaqiyatli sotib olindi!"))
                return redirect("books:my_library")
    else:
        form = CheckoutForm(initial={"address": getattr(buyer, "address", "")})

    return render(
        request,
        "books/checkout.html",
        {
            "book": book,
            "form": form,
            "reviews": book.reviews.select_related("buyer").prefetch_related("replies__author")[:10],
            "liked": book.liked_by(buyer),
        },
    )


@login_required
@require_POST
def toggle_like_view(request, pk):
    """Kitobni yoqtirish / yoqtirishni bekor qilish."""
    book = get_object_or_404(Book, pk=pk)
    like, created = Like.objects.get_or_create(book=book, user=request.user)
    if not created:
        like.delete()
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    return redirect(next_url or book.get_absolute_url())


@buyer_required
def my_library_view(request):
    purchases = Purchase.objects.filter(buyer=request.user).select_related("book", "book__author")

    # Har bir kitobga o'qish holatini biriktiramiz, shunda ro'yxatda
    # "45% o'qildi" va "Davom ettirish" tugmasi ko'rinadi.
    progress_by_book = {
        p.book_id: p
        for p in ReadingProgress.objects.filter(
            user=request.user, book__in=[p.book_id for p in purchases]
        )
    }
    for purchase in purchases:
        purchase.progress = progress_by_book.get(purchase.book_id)

    return render(request, "books/my_library.html", {"purchases": purchases})


@login_required
def review_create_view(request, pk):
    """Baho va izoh qoldirish - sotib olish shart emas."""
    book = get_object_or_404(Book, pk=pk)
    existing = Review.objects.filter(buyer=request.user, book=book).first()
    if request.method == "POST":
        form = ReviewForm(request.POST, instance=existing)
        if form.is_valid():
            review = form.save(commit=False)
            review.book = book
            review.buyer = request.user
            review.save()
            messages.success(request, _("Fikringiz uchun rahmat!"))
    return redirect("books:detail", pk=pk)


@login_required
@require_POST
def reply_create_view(request, review_id):
    """Izohga javob yozish. Javobga javob yozib bo'lmaydi."""
    review = get_object_or_404(Review, pk=review_id)
    form = ReplyForm(request.POST)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.review = review
        reply.author = request.user
        reply.save()
    else:
        messages.error(request, _("Javob bo'sh bo'lmasligi kerak."))
    return redirect("books:detail", pk=review.book_id)


@login_required
@require_POST
def toggle_review_like_view(request, review_id):
    """Izohni yoqtirish / bekor qilish."""
    review = get_object_or_404(Review, pk=review_id)
    like, created = ReviewLike.objects.get_or_create(review=review, user=request.user)
    if not created:
        like.delete()
    return redirect("books:detail", pk=review.book_id)


@login_required
@require_POST
def toggle_reply_like_view(request, reply_id):
    """Javobni yoqtirish / bekor qilish."""
    reply = get_object_or_404(Reply.objects.select_related("review"), pk=reply_id)
    like, created = ReplyLike.objects.get_or_create(reply=reply, user=request.user)
    if not created:
        like.delete()
    return redirect("books:detail", pk=reply.review.book_id)


@seller_required
def my_books_view(request):
    books = Book.objects.filter(seller=request.user).select_related("author", "genre")
    return render(request, "books/my_books.html", {"books": books})


@seller_required
def seller_dashboard_view(request):
    """Sotuvchi kabineti: savdo, daromad va kitoblar kesimidagi statistika."""
    seller = request.user
    sales = Purchase.objects.filter(book__seller=seller).select_related("book", "buyer")

    totals = sales.aggregate(
        revenue=Sum("price_paid"),
        count=Count("id"),
        buyers=Count("buyer", distinct=True),
    )

    # Har bir ko'rsatkich alohida quyi-so'rov (subquery) bilan olinadi.
    #
    # Ularni bitta `annotate` ichida JOIN orqali hisoblab bo'lmaydi: xaridlar,
    # sharhlar va yoqtirishlar bir-biriga ko'payib ketadi (dekart ko'paytmasi)
    # va summa bir necha barobar katta chiqadi. `distinct=True` sanoqni
    # tuzatadi, lekin `Sum` va `Avg` ni tuzatmaydi.
    def per_book(queryset, expression, output_field, default=0):
        agg = queryset.filter(book=OuterRef("pk")).values("book").annotate(value=expression)
        return Coalesce(
            Subquery(agg.values("value")[:1], output_field=output_field),
            Value(default, output_field=output_field),
        )

    money_field = DecimalField(max_digits=12, decimal_places=2)
    books = (
        Book.objects.filter(seller=seller)
        .select_related("author")
        .annotate(
            sales_count=per_book(Purchase.objects, Count("id"), IntegerField()),
            revenue=per_book(Purchase.objects, Sum("price_paid"), money_field, Decimal("0")),
            avg_rating=per_book(Review.objects, Avg("rating"), FloatField(), 0.0),
            likes_total=per_book(Like.objects, Count("id"), IntegerField()),
        )
        .order_by("-revenue", "-sales_count", "title")
    )

    # Oxirgi 30 kunlik savdo - grafik uchun kunma-kun.
    today = timezone.localdate()
    start = today - timedelta(days=29)
    per_day = {
        row["day"]: row
        for row in sales.filter(purchased_at__date__gte=start)
        .annotate(day=TruncDate("purchased_at"))
        .values("day")
        .annotate(amount=Sum("price_paid"), count=Count("id"))
    }
    chart = []
    for offset in range(30):
        day = start + timedelta(days=offset)
        row = per_day.get(day)
        chart.append(
            {
                "day": day,
                "amount": float(row["amount"]) if row else 0.0,
                "count": row["count"] if row else 0,
            }
        )
    # Ustun balandligi butun son bo'lishi kerak: Django shablonda kasr sonni
    # til qoidasiga ko'ra vergul bilan chiqaradi ("100,0"), CSS esa buni
    # tushunmay ustunni umuman chizmaydi.
    chart_max = max((point["amount"] for point in chart), default=0) or 1
    for point in chart:
        point["height"] = int(round(point["amount"] / chart_max * 100))

    month_revenue = sum(point["amount"] for point in chart)

    return render(
        request,
        "books/seller_dashboard.html",
        {
            "revenue": totals["revenue"] or 0,
            "sales_count": totals["count"] or 0,
            "buyers_count": totals["buyers"] or 0,
            "books_count": books.count(),
            "active_books": books.filter(is_active=True).count(),
            "month_revenue": month_revenue,
            "books": books,
            "chart": chart,
            "recent_sales": sales[:10],
            "withdrawals": seller.withdrawals.all()[:5],
        },
    )


@seller_required
def book_create_view(request):
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, seller=request.user)
        if form.is_valid():
            book = form.save(commit=False)
            book.seller = request.user
            book.save()
            messages.success(request, _("Kitob muvaffaqiyatli qo'shildi!"))
            return redirect("books:my_books")
    else:
        form = BookForm(seller=request.user)
    return render(request, "books/book_form.html", {"form": form, "title": _("Yangi kitob qo'shish")})


@seller_required
def book_update_view(request, pk):
    book = get_object_or_404(Book, pk=pk, seller=request.user)
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, instance=book, seller=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Kitob yangilandi."))
            return redirect("books:my_books")
    else:
        form = BookForm(instance=book, seller=request.user)
    return render(request, "books/book_form.html", {"form": form, "title": _("Kitobni tahrirlash")})


@seller_required
@require_POST
def book_delete_view(request, pk):
    book = get_object_or_404(Book, pk=pk, seller=request.user)
    book.delete()
    messages.success(request, _("Kitob o'chirildi."))
    return redirect("books:my_books")


def author_list_view(request):
    authors = Author.objects.all()
    return render(request, "books/author_list.html", {"authors": authors})


def author_detail_view(request, pk):
    author = get_object_or_404(Author, pk=pk)
    books = author.books.filter(is_active=True)
    return render(request, "books/author_detail.html", {"author": author, "books": books})


@seller_required
def author_create_view(request):
    if request.method == "POST":
        form = AuthorForm(request.POST, request.FILES)
        if form.is_valid():
            author = form.save(commit=False)
            author.created_by = request.user
            author.save()
            messages.success(request, _("Muallif qo'shildi."))
            return redirect("books:book_create")
    else:
        form = AuthorForm()
    return render(request, "books/author_form.html", {"form": form})


@seller_required
def genre_create_view(request):
    """Sotuvchi yangi janr qo'shadi.

    Ilgari janrni faqat administrator qo'sha olardi, sotuvchi esa mos janr
    bo'lmasa unga yozishga majbur edi.
    """
    if request.method == "POST":
        form = GenreForm(request.POST)
        if form.is_valid():
            genre = form.save()
            messages.success(
                request, _("\"%(name)s\" janri qo'shildi.") % {"name": genre.name}
            )
            return redirect("books:book_create")
    else:
        form = GenreForm()
    return render(request, "books/genre_form.html", {"form": form, "genres": Genre.objects.all()})


# --- Istaklar ro'yxati ---


@login_required
@require_POST
def toggle_wish_view(request, pk):
    """Kitobni istaklar ro'yxatiga qo'shadi yoki undan olib tashlaydi."""
    book = get_object_or_404(Book, pk=pk)
    wish, created = Wish.objects.get_or_create(user=request.user, book=book)
    if not created:
        wish.delete()
        messages.info(request, _("Istaklar ro'yxatidan olib tashlandi."))
    else:
        messages.success(request, _("Istaklar ro'yxatiga qo'shildi."))
    return redirect(request.POST.get("next") or book.get_absolute_url())


@login_required
def wishlist_view(request):
    wishes = (
        Wish.objects.filter(user=request.user)
        .select_related("book", "book__author")
        .filter(book__is_active=True)
    )
    purchased = set(
        Purchase.objects.filter(buyer=request.user).values_list("book_id", flat=True)
    )
    return render(
        request,
        "books/wishlist.html",
        {"wishes": wishes, "purchased_ids": purchased},
    )


# --- Xaridor va sotuvchi xabarlashuvi ---


@login_required
def conversation_list_view(request):
    """Foydalanuvchining barcha suhbatlari (ikkala rolda ham)."""
    conversations = (
        Conversation.objects.filter(Q(buyer=request.user) | Q(seller=request.user))
        .select_related("book", "buyer", "seller")
        .prefetch_related("messages")
    )
    for conversation in conversations:
        conversation.partner = conversation.other_side(request.user)
        conversation.unread = conversation.unread_count(request.user)
        conversation.last_message = conversation.messages.last()
    return render(request, "books/conversations.html", {"conversations": conversations})


@login_required
def conversation_view(request, pk):
    """Bitta suhbat: xabarlar tarixi va yangi xabar yozish."""
    conversation = get_object_or_404(
        Conversation.objects.select_related("book", "buyer", "seller"), pk=pk
    )
    if request.user.pk not in (conversation.buyer_id, conversation.seller_id):
        raise Http404

    if request.method == "POST":
        text = (request.POST.get("text") or "").strip()
        if text:
            Message.objects.create(conversation=conversation, sender=request.user, text=text[:2000])
            conversation.save(update_fields=["updated_at"])
            _notify_new_message(conversation, request.user, text)
        return redirect("books:conversation", pk=conversation.pk)

    # Ochilganda qarshi tomonning xabarlari o'qilgan deb belgilanadi.
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    return render(
        request,
        "books/conversation.html",
        {
            "conversation": conversation,
            "partner": conversation.other_side(request.user),
            "chat_messages": conversation.messages.select_related("sender"),
        },
    )


@login_required
@require_POST
def conversation_start_view(request, pk):
    """Kitob sahifasidan sotuvchiga savol yozish."""
    book = get_object_or_404(Book.objects.select_related("seller"), pk=pk)
    if book.seller_id == request.user.pk:
        messages.info(request, _("O'zingizga xabar yoza olmaysiz."))
        return redirect(book.get_absolute_url())

    conversation, _created = Conversation.objects.get_or_create(
        book=book, buyer=request.user, defaults={"seller": book.seller}
    )
    text = (request.POST.get("text") or "").strip()
    if text:
        Message.objects.create(conversation=conversation, sender=request.user, text=text[:2000])
        conversation.save(update_fields=["updated_at"])
        _notify_new_message(conversation, request.user, text)
    return redirect("books:conversation", pk=conversation.pk)


def _notify_new_message(conversation, sender, text):
    """Qarshi tomonga Telegram orqali xabar beradi (bot ulangan bo'lsa)."""
    telegram.notify_new_message(conversation, sender, text)
