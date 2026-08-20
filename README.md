# Elektron Kutubxona

Django + Django REST Framework + PostgreSQL asosida qurilgan elektron kitoblar
oldi-sotdi platformasi (marketplace). Sotuvchilar elektron kitob qo'shadi,
xaridorlar sotib oladi, baholaydi va sharh qoldiradi.

## Asosiy imkoniyatlar

- Ro'yxatdan o'tish / kirish, birinchi kirishda **sotuvchi** yoki **sotib oluvchi**
  rolini tanlash.
- Uch tillilik interfeys: **o'zbekcha, ruscha, inglizcha** (Sozlamalar sahifasidan
  yoki header'dagi til tanlagichdan o'zgartiriladi). Kitoblarning o'z tili
  (sotuvchi belgilagan) alohida maydon.
- Ikki tema: **yorug' / qorong'i** (header'dagi tugma yoki Sozlamalar orqali).
- Sotuvchi: kitob qo'shish/tahrirlash/o'chirish, muallif qo'shish, o'z kitoblari
  ro'yxati, Excel/PDF eksport.
- Xaridor: katalogdan qidirish/filtrlash (til, janr, muallif, narx), sotib olish
  (ichki hamyon balansi orqali), 1-5 yulduz baho va sharh qoldirish, "Mening
  kutubxonam" bo'limi.
- **Kitobni brauzerda o'qish**: sotib olingan kitob saytning o'zida ochiladi
  (PDF.js), varaqlash, masshtab, butun ekran va klaviatura bilan boshqarish
  ishlaydi. To'xtagan sahifa saqlanadi - istalgan qurilmadan davom ettiriladi.
- **Sotuvchi kabineti**: daromad, sotilgan nusxalar, xaridorlar soni, oxirgi
  30 kunlik grafik, kitoblar kesimidagi jadval, oxirgi sotuvlar va savdo
  hisobotini Excel'ga yuklash.
- **Pul yechish**: sotuvchi balansdan kartaga pul yechish uchun so'rov
  yuboradi, administrator tasdiqlaydi yoki rad etadi.
- Admin: `#admin` bilan tugaydigan maxfiy kirish (`/boshqaruv-panel/kirish/`ga
  yo'naltiradi), statistika paneli (`/boshqaruv-panel/statistika/`) va to'liq
  Django admin (`/django-boshqaruv-x9f2/`).
- DRF orqali REST API (`/api/`): kitoblar, mualliflar, janrlar, sharhlar,
  xaridlar.
- **Izohlar**: har qanday ro'yxatdan o'tgan foydalanuvchi kitobni yoqtirishi,
  baholashi va izoh yozishi mumkin (sotib olish shart emas). Izohga javob
  yozish va izoh/javobni yoqtirish mumkin - javobga javob yozib bo'lmaydi.
- **AI yordamchi**: kitoblar haqida suhbat, kitob tavsifini avtomatik yozib
  berish va muqova uchun rasm generatsiya qilish.
- **Administrator boshqaruvi**: foydalanuvchini bloklash, o'chirish, shaxsiy
  xabar yuborish, hammaga e'lon tarqatish va parolni yangilash.
- **Parolni tiklash**: parolni unutgan foydalanuvchi email orqali tiklaydi.
  SMTP sozlanmagan bo'lsa, DEBUG rejimida havola ekranda ko'rsatiladi.
- **Hisobni to'ldirish**: xaridor balansini karta orqali to'ldiradi,
  to'ldirishlar tarixi saqlanadi.
- **Istaklar ro'yxati**: kitobni "keyin sotib olaman" deb saqlab qo'yish.
- **Xaridor ↔ sotuvchi xabarlashuvi**: kitob sahifasidan sotuvchiga savol
  yozish, suhbatlar ro'yxati va o'qilmagan xabarlar hisoblagichi.
- **Katalogda saralash**: yangilik, narx, reyting va ommabopligi bo'yicha.
- **Telegram bot**: sayt bilan bitta bazada ishlaydi va sayt qila oladigan
  hamma ishni qiladi — kitob qo'shish, narx o'zgartirish, xarid, sharh,
  yozishuv, hisobni to'ldirish va pul yechish. Botda qilingan ish saytda
  darrov ko'rinadi.
- **Ob-havo**: davlat va shahar tanlanadi (Toshkent, Moskva, Dubay...),
  soatlik va haftalik prognoz saytning o'zida ochiladi.
- **Redis keshi (ixtiyoriy)**: bosh sahifa va katalog keshlanadi, sessiyalar
  tezlashadi, AI so'rovlariga chegara qo'yiladi. Redis'siz ham loyiha to'liq
  ishlaydi.
- PostgreSQL ma'lumotlar bazasi.

## Pullik kitoblar qanday himoyalangan

Kitobning PDF fayli `media/` papkasida **turmaydi** - u yerdagi hamma narsa
manzilni bilgan har kimga ochiq bo'lardi. Fayllar `private_media/` ichida
saqlanadi va faqat quyidagi manzillar orqali beriladi:

| Manzil | Kim ochadi |
|---|---|
| `/kitoblar/<id>/fayl/` | kitobni sotib olgan xaridor, sotuvchining o'zi, administrator |
| `/kitoblar/<id>/yuklab-olish/` | o'sha odamlar (fayl sifatida saqlaydi) |
| `/xususiy-fayl/...` | faqat xodimlar (Django admin panelidagi havola uchun) |

Ruxsati bo'lmagan odamga `403` emas, `404` qaytariladi - u kitobning fayli
bor-yo'qligini ham bilmaydi. REST API ham faylga havola bermaydi: tashqaridan
faqat `has_file` maydoni ko'rinadi.

## Redis (ixtiyoriy)

Loyiha Redis'siz to'liq ishlaydi — u holda Django'ning xotiradagi keshi
qo'llanadi va hech narsa o'rnatish shart emas. Redis ulash uchun `.env`
faylida bitta qatorni to'ldirasiz:

```
REDIS_URL=redis://127.0.0.1:6379/1
```

Ulanganini tekshirish:

```
python manage.py check_cache
```

**Redis nima beradi.** Sinovda o'lchangan natija (bitta kitobli baza):

| Sahifa | Kesh bo'sh | Keshdan |
|---|---|---|
| Bosh sahifa | 18 ta so'rov | **0 ta so'rov** |
| Katalog | 10 ta so'rov | **3 ta so'rov** |

Nima keshlanadi:

- **Bosh sahifa va katalogdagi kitob kartochkalari.** Kartochkada
  foydalanuvchiga xos ma'lumot yo'q, shuning uchun hamma uchun bitta nusxa
  ishlatiladi. Kesh kaliti tilga bog'liq — o'zbekcha va ruscha nusxalar
  aralashib ketmaydi.
- **Sessiyalar** — avval keshdan qidiriladi, topilmasa bazadan olinadi.
- **AI so'rovlari hisoblagichi** — chegara barcha jarayonlar uchun umumiy.

**Kesh qachon yangilanadi.** Kitob, muallif, janr, sharh yoki yoqtirish
o'zgarganda umumiy versiya raqami oshadi va barcha eski nusxalar bir yo'la
ishlamay qoladi (`apps/core/cache.py`). Ya'ni yangi kitob qo'shsangiz u
darhol bosh sahifada ko'rinadi — muddat tugashini kutish shart emas.

**Redis o'chib qolsa** sayt ishlashda davom etadi: loyihada Django'ning
standart Redis backend'i emas, uni o'rab turgan `ResilientRedisCache`
ishlatiladi (`apps/core/cache_backend.py`). U ulanish xatosini yutadi va
"keshda topilmadi" deb ko'rsatadi — sahifa oddiy holicha bazadan
hisoblanadi. Bu holat testlar bilan qamrab olingan (`RedisDownTests`).

> Redis'siz kesh har bir jarayonda alohida bo'ladi. Bitta kompyuterda
> ishlab chiqishda bu sezilmaydi, lekin serverda bir nechta ishchi jarayon
> bo'lsa Redis ulagan ma'qul — aks holda kesh ular orasida bo'linib ketadi.

## AI modeli

Bepul provayderlar model nomlarini tez-tez o'zgartiradi — masalan Groq
`llama-3.3-70b-versatile` ni olib tashlaganda AI yordamchi
`The model does not exist (404)` xatosini bergan edi.

Shuning uchun har bir provayder uchun **bir nechta model** ro'yxati bor
(`apps/core/ai.py`). Birinchisi ishlamasa keyingisi sinaladi, ishlagani
esa eslab qolinadi. Ya'ni model o'chirilsa ham AI yordamchi ishlashda
davom etadi.

Aniq modelni o'zingiz tanlamoqchi bo'lsangiz:

```
AI_MODEL=llama-3.1-8b-instant
```

Bu holda faqat o'sha model ishlatiladi (zaxira sinalmaydi).

Qaysi modellar mavjudligini ko'rish:

```
python manage.py check_ai
```

Xato chiqsa, bu buyruq provayderning o'zidan ro'yxatni so'rab ko'rsatadi.

## AI so'rovlari chegarasi

Bepul API kalitlarining kunlik limiti bor. Chegara bo'lmasa bitta
foydalanuvchi uni bir o'zi tugatib qo'yishi mumkin, shuning uchun har bir
foydalanuvchi uchun soatiga cheklov qo'yilgan (`.env` dan o'zgartiriladi):

```
AI_RATE_LIMIT_MESSAGES=30    # soatiga nechta xabar
AI_RATE_LIMIT_IMAGES=10      # soatiga nechta rasm
AI_RATE_LIMIT_WINDOW=3600    # oyna uzunligi (soniya)
```

Qolgan so'rovlar soni AI sahifasining pastida ko'rinib turadi.

## Telegram bot

Bot saytning ikkinchi yuzi: **xuddi shu ma'lumotlar bazasi** bilan
ishlaydi va sayt qila oladigan deyarli hamma ishni qila oladi — kitob
qo'shishdan tortib pul yechishgacha. Sayt asosiy bo'lib qoladi (u yerda
kengroq ko'rinish va statistika bor), lekin telefonda hamma narsa botdan
bajariladi.

### Botni yaratish

1. Telegram'da **@BotFather** ni oching
2. `/newbot` yozing, botga nom va username bering
3. Bergan tokenini `.env` faylga qo'ying:

```
TELEGRAM_BOT_TOKEN=123456789:AAF...
TELEGRAM_BOT_USERNAME=mening_kutubxona_bot
SITE_URL=http://127.0.0.1:8000
```

Tekshirish va ishga tushirish:

```
python manage.py check_bot     # token, aloqa, webhook, ulangan hisoblar
python bot.py                  # botni ishga tushiradi
```

`bot.py` loyiha ildizidagi qisqa yo'l — ichidan `manage.py bot` ni
chaqiradi. Botning kodi `apps/core/botlib/` ichida. Xohlasangiz
`python manage.py bot` deb ham yozaverasiz, farqi yo'q.

Bot Django serveridan **alohida** jarayonda ishlaydi — ikkita terminal
kerak bo'ladi (biri `runserver`, ikkinchisi `bot`).

### Ikki xil ishlash usuli

| Usul | Qachon | Buyruq |
|---|---|---|
| **Long polling** | Lokal kompyuterda | `python bot.py` |
| **Webhook** | Serverda (Render, VPS) | `python manage.py set_webhook` |

Webhook rejimida bot **alohida jarayonsiz**, saytning ichida ishlaydi:
Telegram yangilikni saytga o'zi yuboradi. Render'ning bepul tarifida
"Background Worker" berilmagani uchun bu yagona yo'l.

Manzilda tasodifiy maxfiy so'z bor va Telegram sarlavhasi ham
tekshiriladi — begona odam botga soxta xabar yubora olmaydi.

```
python manage.py set_webhook            # yoqadi
python manage.py set_webhook --status   # holatini ko'rsatadi
python manage.py set_webhook --off      # o'chiradi (polling'ga qaytish)
```

Ikkalasi bir vaqtda ishlay olmaydi — Telegram `409 Conflict` beradi.

Batafsil: `docs/RENDER.md`.

### Hisobni ulash

Ikki yo'l bor:

**1. Login va parol bilan** — botda `/kirish` yozasiz, so'ng saytdagi
foydalanuvchi nomingiz va parolingizni kiritasiz. Parol yozilgan xabar
darhol o'chiriladi, chat tarixida qolmaydi.

**2. Bir martalik kod bilan** — parolni umuman yozmaslik uchun:

1. Saytda **Sozlamalar → Telegram bot → Kod olish**
2. Chiqqan 6 xonali kodni botga yuborasiz
3. Kod **15 daqiqa** amal qiladi va bir marta ishlatiladi

### Bot nima qila oladi

Bot sayt bilan **bitta ma'lumotlar bazasida** ishlaydi. Botda kitob
qo'shsangiz u saytda darrov ko'rinadi; saytda o'zgartirgan narsangiz
botda ko'rinadi. Hech qanday sinxronizatsiya yo'q — manba bitta.

| Amal | Saytda | Botda |
|---|---|---|
| Katalog, qidiruv | ✅ | ✅ |
| Kitob sotib olish | ✅ | ✅ |
| PDF olish / o'qish | ✅ | ✅ |
| Istaklar, yoqtirish | ✅ | ✅ |
| Baho va sharh yozish | ✅ | ✅ |
| Sotuvchi bilan yozishuv | ✅ | ✅ |
| **Kitob qo'shish** | ✅ | ✅ |
| Narxni o'zgartirish, sotuvdan olish, o'chirish | ✅ | ✅ |
| Hisobni to'ldirish | ✅ | ✅ |
| Pul yechish so'rovi | ✅ | ✅ |
| Til, bildirishnoma, rol | ✅ | ✅ |
| Sotuvchi kabineti (diagramma, Excel) | ✅ | havola |
| AI yordamchi | ✅ | — |

**Botga kirish ikki xil:**

```
/kirish     — saytdagi login va parol bilan
6 xonali kod — Sozlamalar -> Telegram bot -> Kod olish
```

Parol yozilgan xabar **darhol o'chiriladi**, chat tarixida qolmaydi.

**Kitob qo'shish** botda savol-javob tarzida boradi: nom → muallif →
janr → til → sahifa → narx → tavsif → muqova → PDF. Har qadamda
«Bekor qilish» tugmasi bor, `/bekor` buyrug'i ham ishlaydi.

> **Qoidalar bitta joyda.** Xarid `apps/books/services.py`, pul harakati
> `apps/accounts/services.py` da. Sayt ham, bot ham shu funksiyalarni
> chaqiradi — shuning uchun ikkalasida balans, chegara va tekshiruvlar
> bir xil ishlaydi. Ikki nusxada yozilsa, biri o'zgarganda ikkinchisi
> eskirib, pul hisobida farq paydo bo'lardi.

Bildirishnomalar: kitobingiz sotilganda, sizga xabar kelganda, pul yechish
so'rovi ko'rib chiqilganda va administrator e'lon tarqatganda.

> **Xarid mantiqi bitta joyda.** Sayt ham, bot ham `apps/books/services.py`
> dagi bitta funksiyani chaqiradi. Ikki marta yozilsa, biri o'zgarganda
> ikkinchisi eskirib, pul hisobida farq paydo bo'lardi.

### Bot javob bermasa

Avval tashxis buyrug'ini yuring — u sababni o'zi aytadi:

```
python manage.py check_bot
```

Har bir bosqich nimani anglatadi:

| Chiqqan xato | Sabab va yechim |
|---|---|
| `pyTelegramBotAPI o'rnatilmagan` | `pip install -r requirements.txt` |
| `TELEGRAM_BOT_TOKEN bo'sh` | `.env` da token yo'q — @BotFather dan oling |
| `javob olinmadi` | Token noto'g'ri yoki internet yo'q |
| `webhook o'rnatilgan: ...` | Webhook va long polling birga ishlamaydi; `manage.py bot` uni ishga tushishda o'zi o'chiradi |
| `hali hech kim ulanmagan` | Saytda **Sozlamalar → Telegram bot → Kod olish** qiling |

Bot ishga tushdi, lekin xabarga javob bermayaptimi — batafsil jurnal bilan
ishga tushiring:

```
python manage.py bot --debug
```

Har bir kelgan xabar ekranda ko'rinadi. **Ko'rinsa** — muammo handler
ichida (xato jurnalga to'liq chiqadi). **Ko'rinmasa** — xabar botga
yetib kelmayapti: token boshqa botniki yoki bir vaqtda ikkinchi nusxa
ishlab turibdi (bitta tokenda faqat bitta `bot` jarayoni bo'lishi kerak).

## Kirish qachon so'raladi

Sayt mehmonlar uchun ochiq: bosh sahifa, katalog, muallif sahifasi va
kitobning to'liq ma'lumotlari ro'yxatdan o'tmasdan ko'rinadi. Kartochkaning
istalgan joyiga bosilsa kitob sahifasi ochiladi.

Ro'yxatdan o'tish **faqat pul aralashganda** so'raladi:

| Amal | Kirish kerakmi |
|---|---|
| Katalog, kitob ma'lumotlari, mualliflar | Yo'q |
| Sotib olish | **Ha** |
| Izoh, baho, yoqtirish, istaklar | Ha |
| Kitob sotish (sotuvchi) | Ha |

Foydalanuvchi kitob sahifasidan ro'yxatdan o'tsa, rol tanlagandan keyin
**o'sha kitobga qaytariladi** — qaysi kitobni olmoqchi bo'lgani yo'qolmaydi.
Qaytish manzili sessiyada saqlanadi va faqat shu saytning ichki manzillari
qabul qilinadi (begona saytga yo'naltirib bo'lmaydi).

## Testlar

```
python manage.py test
```

Testlar asosan pullik kontent atrofidagi ruxsatlarni va pul harakatini
tekshiradi: kim faylni ocha oladi, xarid pulni to'g'ri o'tkazadimi, pul
yechish so'rovi balansni to'g'ri ushlab qoladimi va rad etilganda
qaytaradimi, kabinetdagi daromad to'g'ri hisoblanadimi.

Telegram bot ham to'liq test bilan qoplangan (`apps/core/test_bot.py`,
51 ta test): soxta bot obyekti orqali butun oqim — login/parol bilan
kirish, kod bilan ulash, kitob qo'shish (PDF bilan), narx o'zgartirish,
xarid, sharh, yozishuv, hisobni to'ldirish va pul yechish — haqiqiy
Telegram'ga chiqmasdan tekshiriladi.

Alohida tekshiriladigan narsa: **botda qilingan ish saytda ko'rinadi.**
Masalan `test_botdan_qoshilgan_kitob_saytda_korinadi` botdan kitob
qo'shadi va keyin saytning katalog sahifasini so'rab, kitob u yerda
chiqqanini tasdiqlaydi.

## Tekshiruv buyruqlari

Nimadir ishlamasa, muammoni o'zi topib beradigan buyruqlar bor:

```
python manage.py check_db     # baza: ulanish, jadvallar, ma'lumotlar
python manage.py check_ai     # AI: .env, kalit, provayder, sinov so'rovi
python manage.py check_cache  # kesh: Redis ulanishi, versiya, chegara
python manage.py check_bot    # Telegram: token, aloqa, ulangan hisoblar
```

## AI yordamchi va bepul API kaliti

Loyiha bir nechta bepul provayderni qo'llab-quvvatlaydi. Bittasini tanlab,
kalitni `.env` fayldagi `AI_API_KEY` ga qo'ying:

| Provayder | Kalit olish manzili | Izoh |
|---|---|---|
| **Gemini** (tavsiya) | https://aistudio.google.com/apikey | Bepul, saxiy limit |
| **Groq** | https://console.groq.com/keys | Bepul, juda tez |
| **OpenRouter** | https://openrouter.ai/keys | Bepul modellar bor |

```
AI_PROVIDER=gemini
AI_API_KEY=bu_yerga_kalitni_qoying
```

**Rasm generatsiyasi** Pollinations orqali ishlaydi va **kalit talab qilmaydi** -
hech narsa sozlamasangiz ham ishlaydi.

AI nima qila oladi: kitob tavsifini yozadi, janr va muallif haqida gapiradi,
kitob tanlashda maslahat beradi, sayt qanday ishlashini tushuntiradi.
AI saytga kitob qo'sha olmaydi - buni faqat sotuvchining o'zi qiladi.

## Administrator imkoniyatlari

`#admin` orqali kirgach `Foydalanuvchilar` bo'limida har bir foydalanuvchi
kartasini ochib:

- shaxsiy xabar yuborish (foydalanuvchi saytga kirganda ko'radi),
- hammaga e'lon tarqatish,
- bloklash / blokni olib tashlash (sabab bilan),
- hisobni o'chirish,
- yangi parol belgilash

mumkin.

> **Parol haqida:** mavjud parolni ko'rsatib bo'lmaydi - Django uni bir
> tomonlama shifrlab (hash) saqlaydi va uni ochish matematik jihatdan
> imkonsiz. Shuning uchun uning o'rniga yangi parol belgilash imkoniyati
> qo'yilgan: siz kiritgan parol saqlanadi va bir marta ekranda ko'rsatiladi.

## Tez boshlash

Loyiha papkasida (`manage.py` yonida) PowerShell oching.

**Birinchi marta:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
notepad .env          # AI kaliti va Telegram tokeni

python manage.py migrate
python manage.py seed_admin
python manage.py runserver
```

**Keyingi safar (sayt):**

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

**Telegram bot — alohida oynada:**

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py check_bot
python bot.py
```

`bot.py` — qisqa yo'l, ichidan `manage.py bot` ni chaqiradi. Ikkalasi bir xil:

```powershell
python bot.py
python manage.py bot
python bot.py --debug        # kelgan har bir xabar ekranda ko'rinadi
```

**Linux / macOS** — faqat ikki qator boshqacha:

```bash
python3 -m venv .venv
source .venv/bin/activate
cp .env.example .env
nano .env

python manage.py migrate
python manage.py seed_admin
python manage.py runserver
```

> Har bir yangi terminalda `Activate.ps1` qaytadan bajariladi — qator
> boshida `(.venv)` ko'rinmasa, buyruqlar ishlamaydi.
>
> PowerShell skriptni taqiqlasa, bir marta:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

## O'rnatish (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
```

Agar PowerShell skript ishga tushirishni taqiqlasa, bir marta quyidagini bajaring:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

So'ng:

```powershell
python manage.py migrate
python manage.py seed_admin
python manage.py runserver
```

Standart holda loyiha **SQLite** bazasida ishlaydi — hech narsa o'rnatish yoki
sozlash shart emas. PostgreSQL'ga o'tish uchun `.env` faylida bitta qatorni
o'zgartirasiz (pastdagi bo'limga qarang).

## O'rnatish (Linux / macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env

python manage.py migrate
python manage.py seed_admin      # .env dagi ADMIN_USERNAME/ADMIN_PASSWORD bilan admin yaratadi
python manage.py runserver
```

Loyihani http://127.0.0.1:8000/ manzilidan ochish mumkin.

## PostgreSQL'ga o'tish

Loyiha PostgreSQL bilan to'liq ishlaydi. Ikki qadam kifoya.

Django `migrate` faqat jadvallarni yaratadi — bazaning o'zi va foydalanuvchi
oldindan mavjud bo'lishi kerak.

**1-qadam — `.env` faylida** `USE_SQLITE` ni `False` qiling.

**2-qadam — baza va foydalanuvchini yarating.** Eng oson yo'li:

```
python manage.py setup_db
```

Bu buyruq `postgres` administratorining parolini so'raydi (PostgreSQL
o'rnatilayotganda belgilangan parol) va `.env` dagi nomlar asosida bazani hamda
foydalanuvchini yaratadi. Takroran ishga tushirish xavfsiz — mavjud bo'lsa
tegmaydi.

Xohlasangiz, o'sha ishni `psql` orqali ham qilish mumkin:

```powershell
# Windows (versiya raqami sizdagiga qarab 16/17/18 bo'lishi mumkin)
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -f scripts\create_db.sql
```

```bash
# Linux / macOS
sudo -u postgres psql -f scripts/create_db.sql
```

**3-qadam:**

```
python manage.py migrate
python manage.py seed_admin
python manage.py runserver
```

> Tarjimalarning tayyor `.mo` fayllari loyiha ichida keladi, shuning uchun
> `compilemessages` buyrug'ini bajarish (va GNU gettext o'rnatish) **shart emas**.
> Faqat tarjima matnlarini o'zgartirsangizgina qayta kompilyatsiya kerak bo'ladi.

## Tez-tez uchraydigan xatolar

**PostgreSQL'ga ulanib bo'lmadi** — ko'pincha `kutubxona_db` bazasi yoki
`kutubxona_user` foydalanuvchisi hali yaratilmagan bo'ladi.
`python manage.py setup_db` buyrug'ini bajaring.

Eski Django versiyalarida bu xato rus tilidagi Windows'da tushunarsiz
`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc2` ko'rinishida chiqardi.
Loyihada `apps/core/db/postgresql/` qobig'i bor — u endi xatoning asl matnini
va nima qilish kerakligini ko'rsatadi.

**`CommandError: Can't find msgfmt`** — GNU gettext o'rnatilmagan. `compilemessages`
buyrug'ini bajarmang, u kerak emas (yuqoridagi izohga qarang).

## Administrator kirishi

Bosh sahifa manzili oxiriga `#admin` qo'shilsa (masalan `http://127.0.0.1:8000/#admin`),
avtomatik ravishda maxfiy admin kirish sahifasiga yo'naltiradi. Standart login/parol
`.env` faylidagi `ADMIN_USERNAME` / `ADMIN_PASSWORD` orqali beriladi (`seed_admin`
buyrug'i ishga tushirilgandan keyin ishlaydi).

### Admin parolini almashtirish

`seed_admin` parolni **faqat hisob birinchi marta yaratilganda**
o'rnatadi. `.env` dagi `ADMIN_PASSWORD` ni keyin o'zgartirsangiz, hisob
allaqachon bor bo'lgani uchun parol eskiligicha qolaveradi. Majburan
yangilash uchun:

```powershell
python manage.py seed_admin --reset-password
```

Serverda (Render kabi, buyruq qo'lda yozib bo'lmaydigan joyda) xuddi
shuni `ADMIN_RESET_PASSWORD=1` o'zgaruvchisi bajaradi — deploydan keyin
uni o'chirib qo'ying, aks holda parol har safar tiklanaveradi.

Parolni butunlay unutgan bo'lsangiz (uni "ko'rish" imkoni yo'q —
bazada qaytarilmaydigan qilib shifrlangan):

```powershell
python manage.py changepassword Saidansaf
```

Batafsil (serverdagi bazaga masofadan ulanish ham): `docs/RENDER.md`.

> **Xavfsizlik bo'yicha eslatma:** `.env` fayli `.gitignore`ga kiritilgan va
> repozitoriyga hech qachon push qilinmaydi. Productionda albatta yangi,
> qat'iy `SECRET_KEY` va admin parolini o'zgartiring.

## Hujjatlar

| Fayl | Mazmuni |
|---|---|
| `docs/LOYIHA-HAQIDA.md` | Loyiha nima qilishi, qaysi texnologiyalar nima uchun ishlatilgani, barcha imkoniyatlar |
| `docs/TEXNIK-TOPSHIRIQ.md` | Rasmiy texnik topshiriq (raqamlangan talablar) |
| `docs/TZ-KESH-VA-CHEGARA.md` | Keshlash va so'rovlar chegarasi uchun alohida TZ |
| `docs/LOYIHA-REJASI.md` | Loyiha rejasi: bajarilgan bosqichlar, qolgan ishlar, xavflar |
| `docs/RENDER.md` | Render.com ga joylashtirish: sayt va bot, cheklovlar bilan |

Har birining Word (`.docx`) varianti ham shu papkada.

## Loyiha tuzilishi

```
config/            # Django sozlamalari va asosiy URL'lar
apps/accounts/      # Foydalanuvchi modeli, ro'yxatdan o'tish/kirish, sozlamalar
apps/books/          # Kitob, Muallif, Janr, Sharh, Xarid modellari, DRF API, eksport
apps/core/           # Bosh sahifa, tema/til, admin, AI, kesh, Telegram bot
templates/          # HTML shablonlar
static/             # CSS/JS
static/vendor/pdfjs/ # PDF.js - kitobni brauzerda o'qish uchun
locale/             # uz/ru/en tarjimalar
media/              # ochiq fayllar: muqovalar, avatarlar
private_media/      # pullik kitob PDF'lari (to'g'ridan-to'g'ri berilmaydi)
```
