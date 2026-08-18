"""Botdagi ko'p qadamli suhbatlar holati.

Telegramda forma yo'q: kitob qo'shish yoki pul yechish kabi amallar
savol-javob ko'rinishida boradi. Shuning uchun "bu foydalanuvchi hozir
qaysi qadamda turibdi" degan ma'lumotni bir joyda saqlash kerak.

Holat xotirada saqlanadi, bazada emas. Sabablari:

  * Bu vaqtinchalik ma'lumot — yarim to'ldirilgan forma. Bot qayta ishga
    tushsa uni yo'qotish muammo emas, foydalanuvchi qaytadan boshlaydi.
  * Bazaga yozilsa har bir bosilgan tugma uchun so'rov ketardi.

Tashlab ketilgan suhbatlar `TIMEOUT` dan keyin o'zi o'chadi — aks holda
foydalanuvchi bir hafta oldin boshlagan "kitob qo'shish" ni davom
ettirmoqchi bo'lgandek ko'rinardi.
"""

import threading
from datetime import timedelta

from django.utils import timezone

TIMEOUT = timedelta(minutes=30)


class Dialog:
    """Bitta chat uchun suhbat holati."""

    def __init__(self, name, step, data=None):
        self.name = name
        self.step = step
        self.data = data or {}
        self.touched_at = timezone.now()

    @property
    def expired(self):
        return timezone.now() - self.touched_at > TIMEOUT

    def touch(self):
        self.touched_at = timezone.now()


class DialogStore:
    """chat_id -> Dialog.

    telebot handlerlarni bir nechta ipda chaqiradi, shuning uchun oddiy
    lug'at o'rniga qulf bilan himoyalangan saqlagich.
    """

    def __init__(self):
        self._items = {}
        self._lock = threading.Lock()

    def get(self, chat_id):
        with self._lock:
            dialog = self._items.get(chat_id)
            if dialog is None:
                return None
            if dialog.expired:
                del self._items[chat_id]
                return None
            return dialog

    def start(self, chat_id, name, step, data=None):
        dialog = Dialog(name, step, data)
        with self._lock:
            self._items[chat_id] = dialog
        return dialog

    def set_step(self, chat_id, step):
        with self._lock:
            dialog = self._items.get(chat_id)
            if dialog:
                dialog.step = step
                dialog.touch()
            return dialog

    def clear(self, chat_id):
        with self._lock:
            self._items.pop(chat_id, None)

    def active(self, chat_id):
        return self.get(chat_id) is not None

    def clear_expired(self):
        """Eskirgan suhbatlarni tozalaydi (xotira o'sib ketmasligi uchun)."""
        with self._lock:
            for chat_id in [c for c, d in self._items.items() if d.expired]:
                del self._items[chat_id]
