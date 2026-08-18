#!/usr/bin/env bash
#
# Render har deploy'da shu skriptni ishga tushiradi.
#
# Tartib muhim: avval kutubxonalar, keyin statik fayllar, oxirida baza.
# Migratsiya oxirida turadi — agar u xato bersa, oldingi versiya ishlab
# turaveradi va sayt uzilmaydi.

set -o errexit   # birinchi xatoda to'xtaydi (xato deploy chiqib ketmasin)

echo "==> Kutubxonalar o'rnatilmoqda"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Statik fayllar yig'ilmoqda"
python manage.py collectstatic --no-input

echo "==> Ma'lumotlar bazasi yangilanmoqda"
python manage.py migrate --no-input

# Administrator hisobi (.env dagi ADMIN_USERNAME/ADMIN_PASSWORD bo'yicha).
# Hisob allaqachon bo'lsa buyruq hech narsa qilmaydi.
echo "==> Administrator hisobi tekshirilmoqda"
python manage.py seed_admin

echo "==> Tayyor"



