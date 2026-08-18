# Render.com ga joylashtirish

Sayt va Telegram bot **bitta xizmatda** ishlaydi. Bot alohida jarayon
emas — u *webhook* orqali saytning ichida ishlaydi.

---

## Nega webhook

Botning ikki xil ishlash usuli bor:

| Usul | Qanday ishlaydi | Nima kerak |
|---|---|---|
| **Long polling** (`manage.py bot`) | Bot Telegramdan "yangilik bormi?" deb doim so'raydi | To'xtamaydigan alohida jarayon |
| **Webhook** | Telegram yangilikni saytga o'zi yuboradi | Faqat HTTPS manzil |

Render'ning **bepul tarifida "Background Worker" berilmaydi** — ya'ni
doim ishlab turadigan ikkinchi jarayonni bepul qo'yib bo'lmaydi. Shuning
uchun Render'da webhook yagona yo'l.

Lokal kompyuterda hech narsa o'zgarmaydi: u yerda `python manage.py bot`
avvalgidek ishlayveradi.

---

## Avval bilib qo'yish kerak bo'lgan uchta cheklov

Bular Render'ning bepul tarifi xususiyati, loyihaning kamchiligi emas.

### 1. Yuklangan kitoblar deploydan keyin yo'qoladi

Bepul tarifda disk **vaqtinchalik**: har yangi deploy yoki qayta
ishga tushishda `media/` va `private_media/` papkalari tozalanadi.
Bazadagi yozuvlar qoladi, PDF fayllar esa yo'qoladi.

Sinov va ko'rsatish uchun bu yetadi. Haqiqiy foydalanish uchun
yechimlar:

| Yechim | Narxi | Izoh |
|---|---|---|
| Render Disk | $1–7/oy | Xizmat sozlamalarida "Disk" qo'shiladi, `/opt/render/project/src` ga ulanadi |
| Cloudflare R2 / Backblaze B2 | ~bepul (10 GB) | `django-storages` orqali ulanadi, kod o'zgaradi |
| Oracle Cloud VPS | bepul | O'z serveringiz, disk doimiy |

### 2. Sayt 15 daqiqadan keyin uxlaydi

Hech kim kirmasa Render bepul xizmatni to'xtatib qo'yadi. Keyingi
so'rov uni uyg'otadi — bu **taxminan 50 soniya** oladi.

Botga ta'siri: uzoq jimlikdan keyingi birinchi xabar kechikadi yoki
javobsiz qolishi mumkin. Telegram yangilikni bir necha marta qayta
yuboradi, shuning uchun odatda ikkinchi urinishda javob keladi.

### 3. Bepul baza 30 kundan keyin o'chadi

Render bepul PostgreSQL'ni 30 kundan keyin o'chirib yuboradi. Muddat
tugashidan oldin zaxira olish yoki pullik tarifga o'tish kerak.

---

## Qadamlar

### 1. Kodni GitHub'ga qo'ying

Render repozitoriyadan oladi, shuning uchun loyiha GitHub'da bo'lishi
kerak.

### 2. Render'da Blueprint yarating

1. https://render.com → ro'yxatdan o'ting (GitHub bilan kirish qulay)
2. **New → Blueprint**
3. Repozitoriyani tanlang

Render loyihadagi `render.yaml` faylini o'qiydi va o'zi yaratadi:

- **kutubxona** — veb-xizmat (sayt + bot)
- **kutubxona-db** — PostgreSQL bazasi

`SECRET_KEY` va administrator paroli avtomatik generatsiya qilinadi.

### 3. Telegram tokenini qo'ying

Render panelida: **kutubxona → Environment**

| Kalit | Qiymat |
|---|---|
| `TELEGRAM_BOT_TOKEN` | @BotFather bergan token |
| `TELEGRAM_BOT_USERNAME` | bot username'i (`@` siz) |
| `AI_API_KEY` | AI yordamchi uchun (ixtiyoriy) |

Saqlagach Render xizmatni qayta ishga tushiradi.

### 4. Administrator parolini oling

**Environment** bo'limida `ADMIN_PASSWORD` qiymatini ko'rasiz —
Render uni o'zi yaratgan. Saqlab qo'ying.

### 5. Webhook'ni yoqing

Sayt ochilgach (`https://kutubxona-xxxx.onrender.com`), Render
panelida **Shell** ni oching va bir marta yozing:

```
python manage.py set_webhook
```

Chiqishi:

```
Webhook yoqildi.
  Manzil: https://kutubxona-xxxx.onrender.com/tg/a1b2c3.../
Endi bot saytning ichida ishlaydi — alohida jarayon kerak emas.
```

Tekshirish:

```
python manage.py set_webhook --status
```

Endi Telegramda botga `/start` yozing.

---

## Nima qayerda ishlaydi

| | Lokal kompyuter | Render |
|---|---|---|
| Sayt | `manage.py runserver` | gunicorn (avtomatik) |
| Bot | `manage.py bot` (polling) | webhook (sayt ichida) |
| Baza | SQLite yoki PostgreSQL | Render PostgreSQL |
| Statik fayllar | Django o'zi | WhiteNoise |
| Kitob PDF'lari | `private_media/` | `private_media/` (vaqtinchalik!) |

---

## Muammolar va yechimlar

| Belgi | Sabab | Yechim |
|---|---|---|
| `Bad Request (400)` | Domen `ALLOWED_HOSTS` da yo'q | Render `RENDER_EXTERNAL_HOSTNAME` ni o'zi qo'shadi; o'z domeningiz bo'lsa `ALLOWED_HOSTS` ga yozing |
| Sayt uslubsiz, qip-yalang'och | Statik fayllar yig'ilmagan | `build.sh` ishlaganini tekshiring (Logs) |
| Formalarda "CSRF verification failed" | `CSRF_TRUSTED_ORIGINS` to'ldirilmagan | O'z domeningiz bo'lsa `https://domen.uz` deb yozing |
| Bot javob bermayapti | Webhook yoqilmagan | `python manage.py set_webhook --status` |
| Bot bir marta javob berib, keyin jim | Xizmat uxlab qolgan | Normal holat — qayta yozing yoki pullik tarifga o'ting |
| `409 Conflict` | Webhook va `manage.py bot` birga ishlayapti | Bittasini tanlang: `set_webhook --off` yoki botni to'xtating |
| Yuklangan kitoblar yo'qoldi | Bepul tarifda disk vaqtinchalik | Yuqoridagi "1-cheklov" bo'limiga qarang |

---

## Webhook'dan polling'ga qaytish

Lokal ishlash yoki VPS'ga ko'chish uchun:

```
python manage.py set_webhook --off
python manage.py bot
```

Ikkalasi bir vaqtda ishlay olmaydi — Telegram `409 Conflict` beradi.

---

## Xavfsizlik

Webhook manzilida tasodifiy maxfiy so'z bor (u tokendan hosil qilinadi)
va Telegram yuboradigan `X-Telegram-Bot-Api-Secret-Token` sarlavhasi
ham tekshiriladi. Ikkalasidan biri mos kelmasa so'rov **404** bilan rad
etiladi — begona odam botga soxta xabar yubora olmaydi.

Bu tekshiruvlar testlar bilan qoplangan (`apps/core/test_webhook.py`).
