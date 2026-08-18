from django.apps import AppConfig


class BooksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.books"

    def ready(self):
        # Kesh invalidatsiyasi signallarini ro'yxatdan o'tkazadi.
        from . import signals  # noqa: F401
