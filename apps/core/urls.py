from django.urls import path

from . import admin_views, ai_views, views

app_name = "core"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("ob-havo/", views.weather_view, name="weather"),
    path("tema-almashtirish/", views.toggle_theme_view, name="toggle_theme"),
    path("til-almashtirish/", views.set_language_view, name="set_language"),
    path("xabar/<int:pk>/oqildi/", views.mark_message_read_view, name="mark_message_read"),
    # AI yordamchi
    path("ai/", ai_views.assistant_view, name="ai_assistant"),
    path("ai/yuborish/", ai_views.assistant_send_view, name="ai_send"),
    path("ai/tozalash/", ai_views.assistant_clear_view, name="ai_clear"),
    path("ai/tavsif/", ai_views.describe_book_view, name="ai_describe"),
    path("ai/rasm/", ai_views.generate_image_view, name="ai_image"),
    # Administrator boshqaruvi
    path("boshqaruv-panel/statistika/", views.admin_dashboard_view, name="admin_dashboard"),
    path("boshqaruv-panel/foydalanuvchilar/", admin_views.user_list_view, name="admin_users"),
    path("boshqaruv-panel/foydalanuvchilar/<int:pk>/", admin_views.user_detail_view, name="admin_user_detail"),
    path("boshqaruv-panel/foydalanuvchilar/<int:pk>/bloklash/", admin_views.user_block_view, name="admin_user_block"),
    path("boshqaruv-panel/foydalanuvchilar/<int:pk>/ochirish/", admin_views.user_delete_view, name="admin_user_delete"),
    path("boshqaruv-panel/foydalanuvchilar/<int:pk>/xabar/", admin_views.user_message_view, name="admin_user_message"),
    path(
        "boshqaruv-panel/foydalanuvchilar/<int:pk>/parol/",
        admin_views.user_reset_password_view,
        name="admin_user_password",
    ),
    path("boshqaruv-panel/elon/", admin_views.broadcast_view, name="admin_broadcast"),
    path("boshqaruv-panel/pul-yechish/", admin_views.withdrawal_list_view, name="admin_withdrawals"),
    path(
        "boshqaruv-panel/pul-yechish/<int:pk>/",
        admin_views.withdrawal_decide_view,
        name="admin_withdrawal_decide",
    ),
]
