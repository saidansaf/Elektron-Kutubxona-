from rest_framework import serializers

from .models import Author, Book, Genre, Purchase, Review


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class AuthorSerializer(serializers.ModelSerializer):
    books_count = serializers.ReadOnlyField()

    class Meta:
        model = Author
        fields = ("id", "full_name", "bio", "birth_date", "photo", "books_count")


class ReviewSerializer(serializers.ModelSerializer):
    buyer = serializers.ReadOnlyField(source="buyer.username")

    class Meta:
        model = Review
        fields = ("id", "book", "buyer", "rating", "comment", "created_at")
        read_only_fields = ("buyer", "created_at")

    def validate(self, attrs):
        request = self.context["request"]
        book = attrs.get("book") or getattr(self.instance, "book", None)
        if not Purchase.objects.filter(buyer=request.user, book=book).exists():
            raise serializers.ValidationError("Sharh qoldirish uchun avval kitobni sotib olishingiz kerak.")
        return attrs

    def create(self, validated_data):
        validated_data["buyer"] = self.context["request"].user
        return super().create(validated_data)


class BookSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source="author.full_name")
    genre_name = serializers.ReadOnlyField(source="genre.name")
    seller_username = serializers.ReadOnlyField(source="seller.username")
    average_rating = serializers.ReadOnlyField()
    reviews_count = serializers.ReadOnlyField()
    # Faylga havola API orqali berilmaydi: kitob pullik va havolani bilgan
    # har kim uni tekinga olib ketardi. Sotuvchi faylni yuklay oladi
    # (write_only), o'qish esa faqat `books:book_file` orqali - u xaridni
    # tekshiradi. Tashqaridan faqat "fayl bormi yoki yo'q" ko'rinadi.
    file = serializers.FileField(write_only=True, required=False, allow_null=True)
    has_file = serializers.SerializerMethodField()

    def get_has_file(self, obj):
        return bool(obj.file)

    class Meta:
        model = Book
        fields = (
            "id",
            "title",
            "author",
            "author_name",
            "genre",
            "genre_name",
            "seller_username",
            "language",
            "pages",
            "price",
            "description",
            "cover",
            "file",
            "has_file",
            "publish_year",
            "is_active",
            "average_rating",
            "reviews_count",
            "created_at",
        )
        read_only_fields = ("created_at",)

    def create(self, validated_data):
        validated_data["seller"] = self.context["request"].user
        return super().create(validated_data)


class PurchaseSerializer(serializers.ModelSerializer):
    book_title = serializers.ReadOnlyField(source="book.title")

    class Meta:
        model = Purchase
        fields = ("id", "book", "book_title", "price_paid", "purchased_at")
        read_only_fields = ("price_paid", "purchased_at")
