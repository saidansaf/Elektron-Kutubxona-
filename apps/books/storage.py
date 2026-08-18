"""Pullik kitob fayllari uchun yopiq saqlagich.

Django `MEDIA_ROOT` ichidagi hamma narsani (muqovalar, avatarlar) to'g'ridan-
to'g'ri beradi - manzilni bilgan har kim ochadi. Kitobning PDF fayli esa
pullik kontent, shuning uchun u `PRIVATE_MEDIA_ROOT` ichida, veb-server
ko'rmaydigan joyda saqlanadi.

Fayl faqat ikki yo'l bilan chiqadi:

* `books:book_file` / `books:book_download` - xaridni tekshirib uzatadi;
* `books:private_file` - `FieldFile.url` chaqirilganda (Django admin) ishlaydi
  va faqat xodimlarga ochiq.

Shu sababli saqlagichga `base_url` beriladi: u bo'lmasa `.url` xato tashlab,
admin panelidagi kitob sahifasini buzardi.
"""

import functools
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    """MEDIA_ROOT dan tashqarida, ochiq berilmaydigan saqlagich.

    Papka va manzil sozlamalardan **har safar** o'qiladi. Agar ular
    konstruktorda bir marta olinsa, testlardagi `override_settings`
    e'tiborsiz qolib, sinov fayllari haqiqiy papkaga yozilardi.
    """

    @property
    def base_location(self):
        return self._value_or_setting(self._location, settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        return self._value_or_setting(self._base_url, settings.PRIVATE_MEDIA_URL)


@functools.cache
def private_storage():
    """Model maydoniga beriladigan chaqiriluvchi (callable).

    Django chaqiriluvchi saqlagichni migratsiyaga havola sifatida yozadi,
    shuning uchun sozlamalar o'zgarsa migratsiyalarni qayta yozish shart emas.
    """
    return PrivateMediaStorage()
