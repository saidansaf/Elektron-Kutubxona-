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

Buni bepul yo'l bilan yumshatish mumkin — pastdagi
["Sayt sekin ishlayapti"](#sayt-sekin-ishlayapti) bo'limiga qarang.

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

Foydalanuvchi nomi — `ADMIN_USERNAME` (standart: `Saidansaf`).

> **Muhim:** `ADMIN_PASSWORD` ni Environment'da o'zgartirish
> **yetarli emas**. `seed_admin` parolni faqat hisob birinchi marta
> yaratilganda o'rnatadi — hisob bor bo'lsa, yangi qiymatga qaramaydi.
> Parolni haqiqatan almashtirish uchun pastdagi bo'limga qarang.

### Admin parolini unutgan bo'lsangiz

Parol bazada qaytarib bo'lmaydigan qilib shifrlangan — uni "ko'rish"
imkoni yo'q. Faqat **yangisini qo'yish** mumkin. Ikki yo'l bor.

**Yo'l 1 — Render orqali (Shell kerak emas):**

1. Render → xizmat → **Environment**
2. `ADMIN_PASSWORD` ga yangi parolni yozing
3. Yangi o'zgaruvchi qo'shing: `ADMIN_RESET_PASSWORD` = `1`
4. **Save** → Render qayta deploy qiladi. `build.sh` dagi `seed_admin`
   parolni yangilaydi.
5. Kirib ko'ring, so'ng **`ADMIN_RESET_PASSWORD` ni o'chirib tashlang**
   (yoki `0` qiling) — aks holda har deploydan keyin parol
   Environment'dagi qiymatga qaytaveradi.

**Yo'l 2 — o'z kompyuteringizdan (tezroq):**

Render → baza → **Connect → External Database URL** ni nusxalang.
So'ng loyiha papkasidagi PowerShell'da:

```powershell
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgres://...External Database URL..."
python manage.py changepassword Saidansaf
```

Buyruq yangi parolni so'raydi va serverdagi bazaga yozadi.
Keyin oynani yoping (`$env:DATABASE_URL` faqat shu oynada qoladi).

Xuddi shu tarzda parolni majburan Environment'dagi qiymatga
tenglashtirish ham mumkin:

```powershell
python manage.py seed_admin --reset-password
```

### 5. Webhook — hech narsa qilish shart emas

`render.yaml` da `AUTO_SET_WEBHOOK=1` turibdi: server har ko'tarilganda
webhook'ni **o'zi yoqadi**. Token qo'shilgach Render xizmatni qayta
ishga tushiradi va bot ishlay boshlaydi.

Telegramda botga `/start` yozib ko'ring.

> **Diqqat:** Render'ning bepul tarifida **"Shell" tugmasi yo'q** —
> serverda qo'lda buyruq yozib bo'lmaydi. Shuning uchun webhook
> avtomatik yoqiladi.

**Tekshirish** (brauzerda, TOKEN o'rniga o'z tokeningiz):

```
https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

Kutilgan javob:

```json
{"ok":true,"result":{
  "url":"https://kutubxona-xxxx.onrender.com/tg/a1b2c3.../",
  "pending_update_count":0
}}
```

`"url":""` bo'lsa — webhook yoqilmagan. Sabablari va yechimi pastdagi
jadvalda.

**Qo'lda yoqish** (kerak bo'lsa, o'z kompyuteringizdan):

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py set_webhook --url https://kutubxona-xxxx.onrender.com
```

Bu buyruq faqat Telegram API'siga murojaat qiladi — serverga kirish
shart emas. `.env` dagi token Render'dagi bilan bir xil bo'lsin.

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

## Sayt sekin ishlayapti

Sekinlikning sabablari bir xil emas. Avval qaysi biri ekanini aniqlang —
davosi ham har xil.

### Qaysi turdagi sekinlik?

| Belgi | Sabab | Davosi |
|---|---|---|
| **Birinchi ochilish 30–60 soniya**, keyingilari tez | Xizmat uxlab qolgan edi | Uyg'oq ushlab turish (pastda) |
| **Hamma sahifa doim 2–5 soniya** | Bepul tarifning protsessori kuchsiz (0.1 CPU) | Faqat pullik tarif (Starter, $7/oy) tuzatadi |
| **Faqat AI sahifasi sekin** | AI provayderi javobini kutish | Normal holat, 5–15 soniya |
| **Rasmlar yo'q, sahifa "yalang'och"** | Statik fayllar yig'ilmagan | Logs'da `collectstatic` ni tekshiring |

### 1. Xizmatni uyg'oq ushlab turish (bepul)

Loyihada shu maqsad uchun eng arzon sahifa bor — u bazaga ham,
shablonga ham murojaat qilmaydi:

```
https://kutubxona-xxxx.onrender.com/ping/
```

Bepul "uptime" xizmatiga shu manzilni har 10 daqiqada chaqirtiring:

1. https://cron-job.org → ro'yxatdan o'ting (bepul)
2. **Create cronjob**
3. URL: yuqoridagi `/ping/` manzili
4. Schedule: **Every 10 minutes**
5. Saqlang

Shundan keyin sayt uxlamaydi va birinchi ochilish ham tez bo'ladi.
Bot ham darrov javob beradi.

> Render bepul tarifda oyiga 750 soat ish vaqti beradi. Bir oy = 730
> soat, ya'ni bitta xizmatni doim uyg'oq ushlab turish chegaraga
> sig'adi. Ikkita bepul xizmatingiz bo'lsa sig'maydi.

### 2. Nima allaqachon qilingan

| Chora | Nima beradi |
|---|---|
| `GZipMiddleware` | HTML/JSON siqiladi — sekin internetda 4–5 barobar kam ma'lumot yuklanadi |
| WhiteNoise + hash'langan fayl nomlari | CSS/JS bir marta yuklanadi, keyin brauzer keshidan olinadi |
| `gthread` ishchilari (`render.yaml`) | Kutayotgan so'rov boshqalarini to'sib qo'ymaydi |
| `CONN_MAX_AGE=600` | Har so'rovda bazaga qaytadan ulanilmaydi |
| Bosh sahifa va katalog keshi | Takroriy so'rovlar bazaga bormaydi |
| `select_related` / `prefetch_related` | Ro'yxatlarda N+1 so'rov yo'q |

> **Diqqat:** `render.yaml` ni o'zgartirish allaqachon yaratilgan
> xizmatga o'z-o'zidan ta'sir qilmaydi. Start Command'ni qo'lda
> yangilash kerak: Render → xizmat → **Settings → Start Command**.

### 3. Redis qo'shish (ixtiyoriy, bepul)

Hozir kesh xotirada saqlanadi va har ishchida alohida. Tashqi Redis
ulansa kesh umumiy bo'ladi va sessiyalar ham tezlashadi.

[Upstash](https://upstash.com) bepul Redis beradi. Ulanish satrini
Render → **Environment** ga `REDIS_URL` nomi bilan qo'ying — kod
o'zgarmaydi, loyiha uni o'zi ko'radi.

### 4. Nima yordam bermaydi

- **Region almashtirish** — Frankfurt O'zbekistonga eng yaqin bepul
  mintaqa, boshqasi faqat yomonlashtiradi.
- **Ishchilar sonini oshirish** — 512 MB xotirada 3+ ishchi sig'maydi,
  natijada xizmat qayta ishga tushaveradi.

---

## Muammolar va yechimlar

| Belgi | Sabab | Yechim |
|---|---|---|
| `Bad Request (400)` | Domen `ALLOWED_HOSTS` da yo'q | Render `RENDER_EXTERNAL_HOSTNAME` ni o'zi qo'shadi; o'z domeningiz bo'lsa `ALLOWED_HOSTS` ga yozing |
| Sayt uslubsiz, qip-yalang'och | Statik fayllar yig'ilmagan | `build.sh` ishlaganini tekshiring (Logs) |
| Formalarda "CSRF verification failed" | `CSRF_TRUSTED_ORIGINS` to'ldirilmagan | O'z domeningiz bo'lsa `https://domen.uz` deb yozing |
| Bot javob bermayapti | Webhook yoqilmagan | `getWebhookInfo` da `"url":""` — Environment'da `AUTO_SET_WEBHOOK=1` va `TELEGRAM_BOT_TOKEN` borligini tekshiring, so'ng **Manual Deploy → Clear build cache & deploy** |
| `getWebhookInfo` da `"last_error_message":"Wrong response from the webhook: 404 Not Found"` | Serverdagi kod eski (webhook qo'shilmagan versiya) | Yangi kodni GitHub'ga push qiling |
| `"last_error_message"` da 502 yoki timeout | Xizmat uxlab qolgan | Normal holat — qayta yozing |
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
