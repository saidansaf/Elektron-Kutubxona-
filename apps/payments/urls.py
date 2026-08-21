from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    # Foydalanuvchi uchun
    path("boshlash/", views.start_view, name="start"),
    path("holat/<int:pk>/", views.result_view, name="result"),
    path("tarix/", views.history_view, name="history"),
    path("test/<int:pk>/", views.test_checkout_view, name="test_checkout"),
    # Provayderlar chaqiradigan manzillar. Payme va Click sozlamalarida
    # aynan shular ko'rsatiladi (docs/TOLOV.md ga qarang).
    path("payme/", views.payme_webhook, name="payme_webhook"),
    path("click/", views.click_webhook, name="click_webhook"),
    # Sozlamalarni tekshirish (faqat administrator ko'radi)
    path("holat/", views.health_view, name="health"),
]
