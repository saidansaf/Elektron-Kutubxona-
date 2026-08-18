#!/usr/bin/env python
"""Telegram botni ishga tushirish uchun qisqa yo'l.

    py bot.py

Bu fayl botning o'zi emas — u shunchaki `manage.py bot` ni chaqiradi.
Botning kodi `apps/core/botlib/` ichida, buyruq esa
`apps/core/management/commands/bot.py` da.

Nega shunday: bot Django ichida ishlaydi — bazaga, modellarga, `.env`
sozlamalariga va tarjimalarga murojaat qiladi. Django esa ishlatishdan
oldin `django.setup()` bilan tayyorlanishi kerak, aks holda
"Apps aren't loaded yet" xatosi chiqadi. Quyidagi ikki qator aynan shuni
qiladi.

Bir xil ish uchun ikkita buyruq bo'lib qolmasin degan bo'lsangiz,
`manage.py` orqali ishlatavering — natija bir xil:

    py manage.py bot            # xuddi shunday
    py manage.py bot --debug    # kelgan har bir xabar ekranda ko'rinadi
"""

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise SystemExit(
            "Django topilmadi. Virtual muhit yoqilganini tekshiring:\n"
            "  .\\.venv\\Scripts\\Activate.ps1     (Windows)\n"
            "  source .venv/bin/activate         (Linux/macOS)\n"
            "so'ng:  pip install -r requirements.txt"
        ) from exc

    # `py bot.py --debug` yozilsa, bayroqlar o'zgarishsiz uzatiladi.
    execute_from_command_line([sys.argv[0], "bot", *sys.argv[1:]])
