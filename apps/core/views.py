import json

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Avg, Count
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.accounts.models import Role
from apps.books.models import Author, Book, Genre, Purchase, Review

from . import cities
from .cache import content_version
from .middleware import DEFAULT_THEME, THEME_SESSION_KEY, VALID_THEMES

User = get_user_model()


def home_view(request):
    # So'rovlar dangasa (lazy): agar shablondagi fragment keshdan olinsa,
    # bu yerdagi so'rovlar bazaga umuman bormaydi.
    latest_books = Book.objects.filter(is_active=True).select_related("author").order_by("-created_at")[:6]
    top_books = (
        Book.objects.filter(is_active=True)
        .annotate(avg_rating=Avg("reviews__rating"), reviews_total=Count("reviews"))
        .order_by("-avg_rating")[:6]
    )

    # Sanoqlar fragmentdan tashqarida (ular foydalanuvchiga bog'liq blok
    # ichida chiqadi), shuning uchun alohida keshlanadi.
    stats = cache.get_or_set(
        f"home-stats:{content_version()}",
        lambda: {
            "books_count": Book.objects.count(),
            "authors_count": Author.objects.count(),
            "users_count": User.objects.count(),
        },
        settings.CACHE_TIMEOUT_HOME,
    )

    return render(
        request,
        "core/home.html",
        {
            "latest_books": latest_books,
            "top_books": top_books,
            "stats": stats,
            "cache_timeout_home": settings.CACHE_TIMEOUT_HOME,
        },
    )


def weather_view(request):
    """Ob-havo sahifasi.

    Foydalanuvchi davlat va shaharni tanlaydi (Toshkent, Moskva, Dubay...).
    Ma'lumotlar brauzerda Open-Meteo'dan bepul, kalitsiz olinadi.

    Avval geolokatsiya so'ralardi: ruxsat berilmasa yoki so'rov e'tiborsiz
    qoldirilsa, sahifa "aniqlanmoqda" holatida qotib qolardi. Endi ro'yxat
    darrov ochiladi, geolokatsiya esa ixtiyoriy tugma bo'lib qoldi.
    """
    return render(
        request,
        "core/weather.html",
        {
            "countries_json": json.dumps(cities.as_json_data(), ensure_ascii=False),
            "labels_json": json.dumps(_weather_labels(), ensure_ascii=False),
            "default_country": cities.DEFAULT_COUNTRY,
            "default_city": cities.DEFAULT_CITY,
        },
    )


def _weather_labels():
    """Ob-havo sahifasidagi barcha matnlar.

    Ular shablonda emas, shu yerda tarjima qilinadi va sahifaga JSON
    bo'lib uzatiladi.

    Sababi jiddiy: ilgari matnlar to'g'ridan-to'g'ri JavaScript ichiga
    `{% trans %}` bilan qo'yilardi. O'zbekcha "Yog'ingarchilik" so'zidagi
    apostrof bir tirnoqli JS satrini yorib yuborgan va butun skript ishga
    tushmagan — sahifa "yuklanmoqda" holatida qotib qolardi. JSON'da
    qo'shtirnoq ham, apostrof ham to'g'ri qochiriladi, shuning uchun bu
    xato boshqa takrorlanmaydi.
    """
    codes = {
        0: ("sun", _("Ochiq havo")),
        1: ("sun-cloud", _("Deyarli ochiq")),
        2: ("sun-cloud", _("Bulutli oraliq")),
        3: ("cloud", _("Bulutli")),
        45: ("fog", _("Tuman")),
        48: ("fog", _("Muzli tuman")),
        51: ("rain", _("Mayda yomg'ir")),
        53: ("rain", _("Yomg'ir")),
        55: ("rain", _("Kuchli yomg'ir")),
        56: ("rain", _("Muzli yomg'ir")),
        57: ("rain", _("Kuchli muzli yomg'ir")),
        61: ("rain", _("Yengil yomg'ir")),
        63: ("rain", _("Yomg'ir")),
        65: ("rain", _("Kuchli yomg'ir")),
        66: ("rain", _("Muzli yomg'ir")),
        67: ("rain", _("Kuchli muzli yomg'ir")),
        71: ("snow", _("Yengil qor")),
        73: ("snow", _("Qor")),
        75: ("snow", _("Kuchli qor")),
        77: ("snow", _("Qor donachalari")),
        80: ("rain", _("Jala")),
        81: ("rain", _("Kuchli jala")),
        82: ("storm", _("Juda kuchli jala")),
        85: ("snow", _("Qor jalasi")),
        86: ("snow", _("Kuchli qor jalasi")),
        95: ("storm", _("Momaqaldiroq")),
        96: ("storm", _("Do'l bilan momaqaldiroq")),
        99: ("storm", _("Kuchli do'l")),
    }
    return {
        "codes": {str(code): [kind, text] for code, (kind, text) in codes.items()},
        "days": [
            _("Yakshanba"), _("Dushanba"), _("Seshanba"), _("Chorshanba"),
            _("Payshanba"), _("Juma"), _("Shanba"),
        ],
        # Brauzerning o'zbekcha sana formati "2026 M08 17" ko'rinishida
        # chiqadi, shuning uchun oy nomlarini o'zimiz beramiz.
        "months": [
            _("yanvar"), _("fevral"), _("mart"), _("aprel"), _("may"), _("iyun"),
            _("iyul"), _("avgust"), _("sentabr"), _("oktabr"), _("noyabr"), _("dekabr"),
        ],
        "today": _("Bugun"),
        "tomorrow": _("Ertaga"),
        "feels": _("his qiladi"),
        "humidity": _("Namlik"),
        "wind": _("Shamol"),
        "windUnit": _("km/soat"),
        "pressure": _("Bosim"),
        "uv": _("UF-indeks"),
        "precip": _("Yog'ingarchilik"),
        "sun": _("Quyosh"),
        "loadFailed": _("Ob-havo ma'lumotini olib bo'lmadi."),
        "geoUnsupported": _("Brauzeringiz joylashuvni aniqlay olmaydi."),
        "geoFailed": _("Joylashuvni aniqlab bo'lmadi. Ro'yxatdan shahar tanlang."),
    }


def _keep_menu_open(url):
    """Manzilga #menu langarini qo'shadi.

    Tema yoki til almashtirilganda sahifa qayta yuklanadi va profil menyusi
    yopilib qolardi. Bu langar orqali menyu qayta ochiladi (static/js/main.js).
    """
    base = (url or "/").split("#")[0]
    return base + "#menu"


@require_POST
def toggle_theme_view(request):
    """Mavzuni almashtiradi.

    `theme` maydoni yuborilsa aynan o'sha mavzu o'rnatiladi (segment tugmalar),
    aks holda yorug' <-> qorong'i almashadi (oddiy tugma).
    """
    requested = request.POST.get("theme")
    if requested in VALID_THEMES:
        new_theme = requested
    else:
        current = request.theme if request.theme in VALID_THEMES else DEFAULT_THEME
        new_theme = "dark" if current == "light" else "light"
    request.session[THEME_SESSION_KEY] = new_theme
    if request.user.is_authenticated:
        request.user.theme = new_theme
        request.user.save(update_fields=["theme"])
    next_url = request.META.get("HTTP_REFERER", "/")
    return HttpResponseRedirect(_keep_menu_open(next_url))


@require_POST
def set_language_view(request):
    """Sarlavhadagi til tanlagichi. Tizimga kirgan bo'lsa User.language ga,
    aks holda LANGUAGE_COOKIE ga yoziladi (LocaleMiddleware o'qiydi)."""
    language = request.POST.get("language")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "/")

    if language not in dict(settings.LANGUAGES):
        return HttpResponseRedirect(next_url)

    response = HttpResponseRedirect(_keep_menu_open(next_url))
    if request.user.is_authenticated:
        request.user.language = language
        request.user.save(update_fields=["language"])
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
    return response


@require_POST
def mark_message_read_view(request, pk):
    """Administrator xabarini o'qilgan deb belgilaydi."""
    from apps.accounts.models import AdminMessage, MessageRead

    if request.user.is_authenticated:
        message = AdminMessage.objects.filter(pk=pk).first()
        if message:
            MessageRead.objects.get_or_create(message=message, user=request.user)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@staff_member_required
def admin_dashboard_view(request):
    stats = {
        "total_users": User.objects.count(),
        "total_sellers": User.objects.filter(role=Role.SELLER).count(),
        "total_buyers": User.objects.filter(role=Role.BUYER).count(),
        "total_authors": Author.objects.count(),
        "total_genres": Genre.objects.count(),
        "total_books": Book.objects.count(),
        "total_active_books": Book.objects.filter(is_active=True).count(),
        "total_purchases": Purchase.objects.count(),
        "total_reviews": Review.objects.count(),
        "total_sales_sum": sum(p.price_paid for p in Purchase.objects.all()),
    }
    recent_users = User.objects.order_by("-date_joined")[:15]
    top_sellers = (
        User.objects.filter(role=Role.SELLER)
        .annotate(books_total=Count("books"))
        .order_by("-books_total")[:10]
    )
    top_books = (
        Book.objects.annotate(avg_rating=Avg("reviews__rating"), reviews_total=Count("reviews"))
        .order_by("-reviews_total")[:10]
    )
    return render(
        request,
        "core/admin_dashboard.html",
        {
            "stats": stats,
            "recent_users": recent_users,
            "top_sellers": top_sellers,
            "top_books": top_books,
        },
    )
