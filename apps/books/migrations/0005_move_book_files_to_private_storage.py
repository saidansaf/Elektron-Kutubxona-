"""Mavjud kitob fayllarini yopiq papkaga ko'chiradi.

Ilgari PDF fayllar `media/book_files/` da yotardi va manzilni bilgan har
kim ularni tekinga yuklab olardi. Endi ular `private_media/book_files/`
ichida, faqat ruxsat tekshiruvidan o'tgan holda beriladi.

Migratsiya faylni ko'chiradi, bazadagi yo'l esa o'zgarmaydi (ikkala
saqlagichda ham u `book_files/<nom>.pdf` bo'lib qolaveradi).
"""

import shutil

from django.conf import settings
from django.db import migrations


def move_to_private(apps, schema_editor):
    Book = apps.get_model("books", "Book")
    for name in Book.objects.exclude(file="").exclude(file=None).values_list("file", flat=True):
        source = settings.MEDIA_ROOT / name
        target = settings.PRIVATE_MEDIA_ROOT / name
        if source.exists() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))


def move_back_to_media(apps, schema_editor):
    Book = apps.get_model("books", "Book")
    for name in Book.objects.exclude(file="").exclude(file=None).values_list("file", flat=True):
        source = settings.PRIVATE_MEDIA_ROOT / name
        target = settings.MEDIA_ROOT / name
        if source.exists() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))


class Migration(migrations.Migration):

    dependencies = [
        ("books", "0004_alter_book_file_readingprogress"),
    ]

    operations = [
        migrations.RunPython(move_to_private, move_back_to_media),
    ]
