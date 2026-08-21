from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("royxatdan-otish/", views.register_view, name="register"),
    path("kirish/", views.LoginPageView.as_view(), name="login"),
    path("chiqish/", views.logout_view, name="logout"),
    path("rol-tanlash/", views.role_select_view, name="role_select"),
    path("sozlamalar/", views.settings_view, name="settings"),
    path("pul-yechish/", views.withdrawal_view, name="withdrawal"),
    path("telegram/", views.telegram_link_view, name="telegram"),
    # Parolni tiklash (Django'ning xavfsiz token tizimi asosida)
    path("parolni-tiklash/", views.PasswordResetRequestView.as_view(), name="password_reset"),
    path("parolni-tiklash/yuborildi/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "parolni-tiklash/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("parolni-tiklash/tayyor/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
