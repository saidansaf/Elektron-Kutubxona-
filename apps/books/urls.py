from django.urls import path

from . import export, views

app_name = "books"

urlpatterns = [
    path("", views.catalog_view, name="catalog"),
    path("<int:pk>/", views.book_detail_view, name="detail"),
    path("<int:pk>/sotib-olish/", views.buy_book_view, name="buy"),
    path("<int:pk>/oqish/", views.book_read_view, name="read"),
    path("<int:pk>/fayl/", views.book_file_view, name="book_file"),
    path("<int:pk>/yuklab-olish/", views.book_download_view, name="book_download"),
    path("<int:pk>/oqish-holati/", views.reading_progress_view, name="reading_progress"),
    path("<int:pk>/yoqtirish/", views.toggle_like_view, name="toggle_like"),
    path("<int:pk>/sharh/", views.review_create_view, name="review_create"),
    path("sharh/<int:review_id>/javob/", views.reply_create_view, name="reply_create"),
    path("sharh/<int:review_id>/yoqtirish/", views.toggle_review_like_view, name="toggle_review_like"),
    path("javob/<int:reply_id>/yoqtirish/", views.toggle_reply_like_view, name="toggle_reply_like"),
    path("mening-kutubxonam/", views.my_library_view, name="my_library"),
    path("<int:pk>/istak/", views.toggle_wish_view, name="toggle_wish"),
    path("istaklarim/", views.wishlist_view, name="wishlist"),
    path("<int:pk>/savol/", views.conversation_start_view, name="conversation_start"),
    path("suhbatlar/", views.conversation_list_view, name="conversations"),
    path("suhbatlar/<int:pk>/", views.conversation_view, name="conversation"),
    path("mening-kitoblarim/", views.my_books_view, name="my_books"),
    path("kabinet/", views.seller_dashboard_view, name="seller_dashboard"),
    path("kabinet/savdo-excel/", export.export_sales_excel, name="export_sales_excel"),
    path("qoshish/", views.book_create_view, name="book_create"),
    path("<int:pk>/tahrirlash/", views.book_update_view, name="book_update"),
    path("<int:pk>/ochirish/", views.book_delete_view, name="book_delete"),
    path("mualliflar/", views.author_list_view, name="author_list"),
    path("mualliflar/<int:pk>/", views.author_detail_view, name="author_detail"),
    path("mualliflar/qoshish/", views.author_create_view, name="author_create"),
    path("janrlar/qoshish/", views.genre_create_view, name="genre_create"),
    path("export/kitoblar/excel/", export.export_books_excel, name="export_books_excel"),
    path("export/kitoblar/pdf/", export.export_books_pdf, name="export_books_pdf"),
    path("export/mualliflar/excel/", export.export_authors_excel, name="export_authors_excel"),
    path("export/mualliflar/pdf/", export.export_authors_pdf, name="export_authors_pdf"),
]
