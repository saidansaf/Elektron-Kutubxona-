"""Kitoblar o'zgarganda keshlangan sahifalarni eskirgan deb belgilaydi.

Keshlangan fragmentlarni birma-bir o'chirish o'rniga umumiy versiya
raqamini oshiramiz - shunda barcha eski nusxalar bir yo'la ishlamay
qoladi (apps/core/cache.py).
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.cache import bump_content_version

from .models import Author, Book, Genre, Like, Review

# Bosh sahifa va katalogda ko'rinadigan hamma narsa
WATCHED_MODELS = (Book, Author, Genre, Review, Like)


@receiver(post_save)
@receiver(post_delete)
def invalidate_content_cache(sender, **kwargs):
    if sender in WATCHED_MODELS:
        bump_content_version()
