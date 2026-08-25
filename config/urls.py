from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import AdminLoginView
from apps.books.views import private_file_view
from apps.core.botlib.webhook import telegram_webhook
from apps.core.pwa_views import manifest_view, offline_view, service_worker_view

urlpatterns = [
    # Ilova qilib o'rnatish uchun (PWA). Bu ikkalasi saytning ILDIZIDA
    # turishi shart: service worker faqat o'zi turgan papkadan pastdagi
    # manzillarni boshqara oladi (apps/core/pwa_views.py ga qarang).
    path("manifest.webmanifest", manifest_view, name="manifest"),
    path("sw.js", service_worker_view, name="service_worker"),
    path("oflayn/", offline_view, name="offline"),
    # Telegram yangiliklari (webhook rejimi). Manzilda maxfiy so'z bor,
    # shuning uchun uni tashqaridan topib bo'lmaydi.
    path("tg/<str:secret>/", telegram_webhook, name="telegram_webhook"),
    # Yopiq saqlanadigan kitob fayllari (faqat xodimlar uchun, `.url` uchun)
    path("xususiy-fayl/<path:path>", private_file_view, name="private_file"),
    # Haqiqiy Django admin - taxminan aniqlab bo'lmaydigan manzilda
    path("django-boshqaruv-x9f2/", admin.site.urls),
    # "#admin" orqali ochiladigan maxfiy administrator kirish sahifasi
    path("boshqaruv-panel/kirish/", AdminLoginView.as_view(), name="admin_login"),
    path("hisobim/", include("apps.accounts.urls")),
    path("kitoblar/", include("apps.books.urls")),
    path("tolov/", include("apps.payments.urls")),
    path("api/", include("apps.books.api_urls")),
    path("api-auth/", include("rest_framework.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
