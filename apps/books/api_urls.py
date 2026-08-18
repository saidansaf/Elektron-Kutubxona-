from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register("genres", api_views.GenreViewSet, basename="api-genre")
router.register("authors", api_views.AuthorViewSet, basename="api-author")
router.register("books", api_views.BookViewSet, basename="api-book")
router.register("reviews", api_views.ReviewViewSet, basename="api-review")
router.register("my-purchases", api_views.MyPurchaseViewSet, basename="api-my-purchase")

urlpatterns = router.urls
