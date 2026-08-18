from django.contrib import admin

from .models import Author, Book, Genre, Like, Purchase, Reply, Review


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "books_count")
    search_fields = ("name",)

    def books_count(self, obj):
        return obj.books.count()

    books_count.short_description = "Kitoblar soni"


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "books_count", "created_at")
    search_fields = ("full_name",)
    readonly_fields = ("created_at",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "seller", "language", "price", "pages", "average_rating", "is_active", "created_at")
    list_filter = ("language", "genre", "is_active")
    search_fields = ("title", "author__full_name", "seller__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "created_at")


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ("review", "author", "created_at")
    search_fields = ("text", "author__username")


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("buyer", "book", "price_paid", "card_last4", "purchased_at")
    search_fields = ("buyer__username", "book__title")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("book", "buyer", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("book__title", "buyer__username")
