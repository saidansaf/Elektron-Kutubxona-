from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Author, Book, Genre, Purchase, Review
from .permissions import IsBuyer, IsOwnerSellerOrReadOnly, IsSellerOrReadOnly
from .serializers import (
    AuthorSerializer,
    BookSerializer,
    GenreSerializer,
    PurchaseSerializer,
    ReviewSerializer,
)


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsSellerOrReadOnly]


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [IsSellerOrReadOnly]
    search_fields = ["full_name"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related("author", "genre", "seller").all()
    serializer_class = BookSerializer
    permission_classes = [IsSellerOrReadOnly, IsOwnerSellerOrReadOnly]
    filterset_fields = ["language", "genre", "author", "is_active"]
    search_fields = ["title", "author__full_name"]
    ordering_fields = ["price", "created_at", "pages"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in ("list", "retrieve"):
            return qs.filter(is_active=True)
        return qs.filter(seller=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsBuyer])
    def buy(self, request, pk=None):
        book = self.get_object()
        buyer = request.user

        if Purchase.objects.filter(buyer=buyer, book=book).exists():
            return Response({"detail": "Kitob allaqachon sotib olingan."}, status=status.HTTP_400_BAD_REQUEST)
        if buyer.balance < book.price:
            return Response({"detail": "Mablag' yetarli emas."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            buyer.balance -= book.price
            buyer.save(update_fields=["balance"])
            book.seller.balance += book.price
            book.seller.save(update_fields=["balance"])
            purchase = Purchase.objects.create(buyer=buyer, book=book, price_paid=book.price)

        return Response(PurchaseSerializer(purchase).data, status=status.HTTP_201_CREATED)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("book", "buyer").all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ["book", "rating"]

    def get_queryset(self):
        qs = super().get_queryset()
        book_id = self.request.query_params.get("book")
        if book_id:
            qs = qs.filter(book_id=book_id)
        return qs


class MyPurchaseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PurchaseSerializer
    permission_classes = [IsBuyer]

    def get_queryset(self):
        return Purchase.objects.filter(buyer=self.request.user).select_related("book")
