# TEXNIK TOPSHIRIQ

## Keshlash quyi tizimi va so'rovlar chegarasi

### "Elektron Kutubxona" loyihasi uchun

---

### Hujjat haqida

| Maydon | Qiymat |
|---|---|
| Hujjat turi | Texnik topshiriq (quyi tizim uchun) |
| Quyi tizim | Keshlash (Redis) va so'rovlar chegarasi (rate limiting) |
| Asosiy hujjat | `docs/TEXNIK-TOPSHIRIQ.md` (3.17 va 3.18-bo'limlar) |
| Versiya | 1.0 |
| Ishlab chiquvchi | Saidansaf |
| Texnologiya | Django 5.2 · Redis 5+ · redis-py |

---

## 1. Muammoning qo'yilishi

### 1.1. Birinchi muammo — takroriy hisob-kitob

Bosh sahifa har ochilganda bir xil ish qaytadan bajariladi: eng yangi olti
kitob, eng yuqori baholangan olti kitob, ularning o'rtacha bahosi,
sharhlari va yoqtirishlari soni. O'lchov shuni ko'rsatdi:

```
Bosh sahifa  -> 18 ta SQL so'rov, 364 ms
Katalog      -> 10 ta SQL so'rov
```

Bu ma'lumotlar kunlar davomida o'zgarmasligi mumkin, lekin har bir
tashrifchi uchun noldan hisoblanadi. Foydalanuvchilar soni ortganda bu
bazaga keraksiz yuk beradi.

### 1.2. Ikkinchi muammo — AI kalitini bir odam tugatib qo'yishi

Loyihada bepul AI provayderlari ishlatiladi (Gemini, Groq, OpenRouter).
Ularning barchasida kunlik yoki daqiqalik so'rov limiti bor. Hozir bitta
foydalanuvchi cheksiz so'rov yubora oladi — u limitni bir o'zi tugatsa,
qolgan barcha foydalanuvchilar uchun AI ishlamay qoladi.

### 1.3. Cheklov — loyiha oddiy noutbukda ishlashi kerak

Loyiha o'quv maqsadida yozilgan va uni turli kompyuterlarda ishga tushirish
kerak bo'ladi. Redis'ni majburiy qilib qo'yish o'rnatishni murakkablashtirar
va "avval Redis o'rnating" degan qo'shimcha shart paydo bo'lardi. Shuning
uchun **Redis ixtiyoriy bo'lishi shart**.

---

## 2. Maqsad va vazifalar

### 2.1. Maqsad

Saytning eng ko'p ochiladigan sahifalarini tezlashtirish va tashqi AI
xizmatidan foydalanishni adolatli taqsimlash — bunda loyihaning oddiy
o'rnatilishini buzmasdan.

### 2.2. Vazifalar

1. Redis'ni **ixtiyoriy** kesh sifatida ulash: sozlanmagan bo'lsa loyiha
   avvalgidek ishlashi kerak.
2. Bosh sahifa va katalogdagi og'ir qismlarni keshlash.
3. Keshni **o'z vaqtida yangilash**: yangi kitob darhol ko'rinishi kerak.
4. AI so'rovlariga foydalanuvchi bo'yicha chegara qo'yish.
5. Redis nosozligiga chidamlilik: kesh ishlamasa sayt yiqilmasligi kerak.
6. Kesh holatini tekshiradigan tashxis buyrug'i.

### 2.3. Atamalar

| Atama | Ta'rifi |
|---|---|
| **Kesh** | Hisoblangan natijani vaqtincha saqlab, keyingi safar qaytadan hisoblamaslik |
| **Backend** | Kesh qayerda saqlanishi (Redis, xotira) |
| **Fragment kesh** | Sahifaning bir bo'lagini keshlash (butun sahifani emas) |
| **Invalidatsiya** | Eskirgan kesh yozuvini ishlatishdan to'xtatish |
| **Kontent versiyasi** | Barcha keshlangan fragmentlarga umumiy bo'lgan raqam |
| **Rate limiting** | Vaqt oynasida so'rovlar sonini cheklash |
| **Oyna (window)** | Chegara hisoblanadigan vaqt oralig'i |
| **LocMemCache** | Django'ning jarayon xotirasidagi standart keshi |

---

## 3. Funksional talablar

### 3.1. Kesh backend'ini tanlash

| № | Talab |
|---|---|
| K-1.1 | Kesh manzili `.env` faylidagi `REDIS_URL` o'zgaruvchisidan olinadi |
| K-1.2 | `REDIS_URL` to'ldirilgan bo'lsa Redis ishlatiladi |
| K-1.3 | `REDIS_URL` bo'sh bo'lsa Django'ning xotiradagi keshi ishlatiladi |
| K-1.4 | Backend tanlash avtomatik — foydalanuvchi kodga tegmaydi |
| K-1.5 | Redis kalitlariga `kutubxona` prefiksi qo'yiladi (bir Redis'da bir nechta loyiha turishi mumkin) |
| K-1.6 | Ulanish kutish vaqti 2 soniyadan oshmasligi kerak |

### 3.2. Sahifalarni keshlash

| № | Talab |
|---|---|
| K-2.1 | Bosh sahifadagi "Yangi kitoblar" bloki keshlanadi |
| K-2.2 | Bosh sahifadagi "Eng yuqori baholangan" bloki keshlanadi |
| K-2.3 | Bosh sahifadagi kitob va muallif sanoqlari keshlanadi |
| K-2.4 | Katalogdagi natijalar ro'yxati keshlanadi |
| K-2.5 | Keshlanadigan bloklarda foydalanuvchiga xos ma'lumot bo'lmasligi shart |
| K-2.6 | Muddat `.env` dan sozlanadi: bosh sahifa 300 s, katalog 180 s (standart) |

> **Nima uchun butun sahifa emas.** Sahifada foydalanuvchiga bog'liq
> qismlar bor: avatar, "Mening kutubxonam" havolasi, administrator
> xabarlari. Butun sahifa keshlansa, bir foydalanuvchining shaxsiy
> ma'lumoti boshqasiga ko'rinib qolardi. Shuning uchun faqat kitob
> kartochkalari keshlanadi — ularda shaxsiy hech narsa yo'q.

### 3.3. Kesh kalitlari

| № | Talab |
|---|---|
| K-3.1 | Kalitga interfeys tili qo'shiladi — tarjimalar aralashib ketmasligi uchun |
| K-3.2 | Kalitga kontent versiyasi qo'shiladi |
| K-3.3 | Katalog kaliti barcha filtrlarni va sahifa raqamini o'z ichiga oladi |
| K-3.4 | Filtrlar tartibi kalitga ta'sir qilmasligi kerak |
| K-3.5 | Filtr qiymatlaridagi ortiqcha probellar kalitga ta'sir qilmasligi kerak |

**Katalog kaliti tuzilishi:**

```
q=<qidiruv>|language=<til>|genre=<janr>|author=<muallif>|
min_price=<min>|max_price=<maks>|page=<sahifa>
```

Ya'ni `?language=uz&q=abc` va `?q=abc&language=uz` bir xil kalit beradi va
keshda bitta yozuv egallaydi.

### 3.4. Kesh invalidatsiyasi

| № | Talab |
|---|---|
| K-4.1 | Kitob qo'shilsa, tahrirlansa yoki o'chirilsa kesh yangilanadi |
| K-4.2 | Muallif yoki janr o'zgarsa kesh yangilanadi |
| K-4.3 | Sharh yoki yoqtirish qo'shilsa/o'chirilsa kesh yangilanadi |
| K-4.4 | Invalidatsiya avtomatik — sotuvchi hech narsa bosmaydi |
| K-4.5 | Muddat tugashini kutish shart emas: yangi kitob darhol ko'rinadi |

**Algoritm — versiya raqami orqali.** Keshdagi yozuvlarni birma-bir topib
o'chirish (masalan, barcha filtr kombinatsiyalarini) amalda imkonsiz:
ularning soni juda ko'p. Buning o'rniga barcha kalitlarga umumiy versiya
raqami qo'shiladi:

```
template.cache.home-latest.<til>.<versiya>
template.cache.catalog-grid.<til>.<versiya>.<filtrlar>
```

Kitob o'zgarganda versiya bittaga oshadi. Eski kalitlar hech kim tomonidan
so'ralmay qoladi va muddati tugagach Redis ularni o'zi o'chiradi.

### 3.5. AI so'rovlari chegarasi

| № | Talab |
|---|---|
| K-5.1 | Har bir foydalanuvchi uchun oynada cheklangan miqdorda AI xabari |
| K-5.2 | Rasm generatsiyasi alohida hisoblanadi |
| K-5.3 | Kitob tavsifini yozdirish xabarlar hisobiga kiradi |
| K-5.4 | Standart qiymatlar: 30 xabar, 10 rasm, oyna 1 soat |
| K-5.5 | Qiymatlar `.env` dan o'zgartiriladi |
| K-5.6 | Chegara oshganda `429 Too Many Requests` va tushunarli matn qaytariladi |
| K-5.7 | Xabarda qancha kutish kerakligi ko'rsatiladi |
| K-5.8 | Qolgan so'rovlar soni AI sahifasida ko'rinadi va har javobdan keyin yangilanadi |
| K-5.9 | Foydalanuvchilar hisobi bir-biriga ta'sir qilmaydi |
| K-5.10 | Bo'sh yoki noto'g'ri so'rov chegarani sarflamaydi |

**Oyna qanday ishlaydi.** Hisob birinchi so'rovdan boshlanadi va oyna
tugagach noldan boshlanadi. Har bir so'rov oynani uzaytirmaydi — aks holda
faol foydalanuvchi hech qachon "ozod" bo'lmasdi.

### 3.6. Sessiyalar

| № | Talab |
|---|---|
| K-6.1 | Redis ulangan bo'lsa sessiyalar avval keshdan qidiriladi |
| K-6.2 | Keshda topilmasa bazadan olinadi — sessiya yo'qolmaydi |
| K-6.3 | Redis sozlanmagan bo'lsa sessiyalar faqat bazada saqlanadi |

### 3.7. Tashxis buyrug'i

`python manage.py check_cache` quyidagilarni ketma-ket tekshiradi:

| № | Bosqich |
|---|---|
| K-7.1 | Qaysi backend ishlatilyapti (Redis yoki xotira) |
| K-7.2 | Keshga yozib, qaytib o'qib ko'rish |
| K-7.3 | Kontent versiyasi oshayaptimi |
| K-7.4 | So'rovlar chegarasi hisoblagichi ishlayaptimi |
| K-7.5 | Sessiyalar qayerdan o'qilyapti |
| K-7.6 | Keshlash muddatlari |

Ulanib bo'lmasa — xatoning asl matni va nima qilish kerakligi ko'rsatiladi.

---

## 4. Nofunksional talablar

### 4.1. Nosozliklarga chidamlilik

| № | Talab |
|---|---|
| K-8.1 | Redis o'chib qolsa sayt ishlashda davom etadi |
| K-8.2 | Ulanish xatosi "keshda topilmadi" holati sifatida qabul qilinadi |
| K-8.3 | Sahifa oddiy holicha bazadan hisoblanadi |
| K-8.4 | Kesh ishlamasa so'rovlar chegarasi foydalanuvchini bloklamaydi |
| K-8.5 | Kesh xatolari jurnalga (log) yoziladi, lekin foydalanuvchiga ko'rsatilmaydi |
| K-8.6 | Kesh butunlay tozalansa tizim o'zini tiklaydi |

> **Muhim eslatma.** Django'ning standart `RedisCache` backend'i ulanish
> uzilganda xatoni yuqoriga uzatadi va sahifa `500` xatosi bilan tugaydi.
> Shuning uchun loyihada uning ustiga `ResilientRedisCache` qobig'i
> yozilgan — u ulanish xatolarini yutadi. Bu talab test bilan tekshiriladi
> (yopiq portga ulanib ko'riladi va sahifalar `200` qaytarishi tasdiqlanadi).

### 4.2. Xavfsizlik

| № | Talab |
|---|---|
| K-9.1 | Keshda faqat ommaviy ma'lumot saqlanadi (kitob kartochkalari) |
| K-9.2 | Shaxsiy ma'lumot (balans, xaridlar, xabarlar) keshlanmaydi |
| K-9.3 | Kalitlar prefiks bilan ajratiladi |
| K-9.4 | Chegara hisoblagichi foydalanuvchi identifikatoriga bog'lanadi |

### 4.3. Unumdorlik

| № | Talab |
|---|---|
| K-10.1 | Keshdan berilgan bosh sahifa bazaga so'rov yubormasligi kerak |
| K-10.2 | Redis'ga ulanish kutish vaqti 2 soniyadan oshmasligi kerak |
| K-10.3 | Kesh yozuvlari muddati tugagach avtomatik o'chirilishi kerak |

---

## 5. Arxitektura

### 5.1. Komponentlar

| Fayl | Vazifasi |
|---|---|
| `config/settings.py` | Backend tanlash, muddatlar, chegara qiymatlari |
| `apps/core/cache.py` | Kontent versiyasi va chegara funksiyalari |
| `apps/core/cache_backend.py` | Xatolarga chidamli Redis backend'i |
| `apps/books/signals.py` | Model o'zgarganda versiyani oshirish |
| `apps/core/context_processors.py` | Versiyani shablonga uzatish |
| `apps/core/management/commands/check_cache.py` | Tashxis buyrug'i |
| `templates/core/home.html` | Bosh sahifa fragment keshi |
| `templates/books/catalog.html` | Katalog fragment keshi |
| `apps/books/views.py` | Katalog kesh kalitini yasash |
| `apps/core/ai_views.py` | AI so'rovlariga chegara qo'llash |

### 5.2. So'rovning yo'li

```
Foydalanuvchi
     │
     ▼
  Django view  ──► ma'lumotlar bazasi so'rovlari (dangasa, hali bajarilmaydi)
     │
     ▼
  Shablon  ──►  {% cache %} tegi
                    │
                    ├── keshda bor      ──► tayyor HTML qaytariladi
                    │                        (bazaga umuman borilmaydi)
                    │
                    └── keshda yo'q     ──► so'rovlar bajariladi,
                                             HTML yasaladi va keshga yoziladi
```

Bu yerda muhim nozik jihat: Django'ning so'rovlari **dangasa** (lazy).
Agar fragment keshdan olinsa, view'dagi so'rovlar umuman bajarilmaydi —
shuning uchun 18 ta so'rov 0 ga tushadi.

### 5.3. Invalidatsiya oqimi

```
Sotuvchi kitob qo'shdi
     │
     ▼
  Book.save()
     │
     ▼
  post_save signali  ──►  bump_content_version()
                                │
                                ▼
                        versiya: 7 ──► 8
                                │
                                ▼
                   Barcha kalitlar o'zgardi:
                   ...home-latest.uz.7  (endi hech kim so'ramaydi)
                   ...home-latest.uz.8  (yangi, bo'sh — qayta hisoblanadi)
```

---

## 6. Konfiguratsiya

`.env` faylidagi o'zgaruvchilar:

| O'zgaruvchi | Standart | Vazifasi |
|---|---|---|
| `REDIS_URL` | *(bo'sh)* | Redis manzili. Bo'sh bo'lsa xotiradagi kesh |
| `CACHE_TIMEOUT_HOME` | `300` | Bosh sahifa keshi muddati (soniya) |
| `CACHE_TIMEOUT_CATALOG` | `180` | Katalog keshi muddati (soniya) |
| `AI_RATE_LIMIT_MESSAGES` | `30` | Oynada nechta AI xabari |
| `AI_RATE_LIMIT_IMAGES` | `10` | Oynada nechta rasm |
| `AI_RATE_LIMIT_WINDOW` | `3600` | Oyna uzunligi (soniya) |

Redis'ni yoqish:

```
REDIS_URL=redis://127.0.0.1:6379/1
```

Chiqarib tashlash — shu qatorni bo'sh qoldirish kifoya, boshqa hech narsa
o'zgartirilmaydi.

---

## 7. Testlash

Quyi tizim uchun **21 ta avtomatik test** yozilgan (`apps/core/tests.py`).

| Test sinfi | Nimani tekshiradi | Testlar |
|---|---|---|
| `ContentVersionTests` | Versiya oshishi, kesh tozalanganda tiklanishi | 3 |
| `RateLimitTests` | Chegara mantiqi, foydalanuvchilar ajratilishi | 5 |
| `AiRateLimitViewTests` | AI so'rovlarida `429`, rasm chegarasi alohida | 3 |
| `RedisDownTests` | Redis o'chganda sahifalar `200` qaytarishi | 4 |
| `PageCacheTests` | Keshlanish, invalidatsiya, filtrlar ajratilishi | 6 |

Ishga tushirish:

```
python manage.py test apps.core
```

Testlar **Redis talab qilmaydi** — xotiradagi kesh xuddi shu interfeysni
beradi, shuning uchun mantiq ikkalasida bir xil tekshiriladi.
`RedisDownTests` esa ataylab yopiq portga ulanib ko'radi.

### 7.1. Asosiy tekshiruvlar

| Tekshiruv | Kutilgan natija |
|---|---|
| Bosh sahifani ikki marta ochish | Ikkinchi marta **0 ta SQL so'rov** |
| Yangi kitob qo'shish | Keyingi ochilishda kitob **darhol ko'rinadi** |
| Kitobni o'chirish | Keyingi ochilishda kitob **yo'qoladi** |
| `?language=uz` va `?language=ru` | **Turli natijalar**, aralashib ketmaydi |
| Chegaradan oshiq so'rov | HTTP **429** |
| Bo'sh xabar yuborish | HTTP **400**, chegara **sarflanmaydi** |
| Redis o'chgan holat | Sahifalar HTTP **200** |

---

## 8. O'lchangan natijalar

Sinov muhitida (bitta kitobli baza, Redis lokal):

| Sahifa | Kesh bo'sh | Keshdan | Farq |
|---|---|---|---|
| Bosh sahifa | 18 ta so'rov, 364 ms | 0 ta so'rov, 4 ms | so'rovlar butunlay yo'qoldi |
| Katalog | 10 ta so'rov | 3 ta so'rov | 70% kamaydi |
| Filtrlangan katalog | 10 ta so'rov | 3 ta so'rov | alohida keshlanadi |

Katalogda 3 ta so'rov qolishining sababi: sahifalash uchun umumiy sonni
bilish kerak (`COUNT`), bu esa fragmentdan tashqarida bajariladi.

---

## 9. Cheklovlar va eslatmalar

1. **Redis'siz kesh har bir jarayonda alohida bo'ladi.** Bitta kompyuterda
   ishlab chiqishda bu sezilmaydi, lekin serverda bir nechta ishchi jarayon
   ishlasa kesh ular orasida bo'linadi va samarasi kamayadi. Production
   uchun Redis tavsiya etiladi.

2. **Kesh faqat ommaviy ma'lumot uchun.** Foydalanuvchiga xos hech narsa
   keshlanmaydi. Kelajakda keshlash kengaytirilsa, bu qoidaga rioya
   qilish shart — aks holda bir foydalanuvchining ma'lumoti boshqasiga
   ko'rinib qolishi mumkin.

3. **Chegara — himoya vositasi, hisob-kitob emas.** Kesh ishlamay qolsa
   chegara tekshirilmaydi. Bu ataylab shunday: foydalanuvchini xato tufayli
   bloklab qo'ygandan ko'ra o'tkazib yuborgan afzal.

4. **Redis ma'lumotlar bazasi sifatida ishlatilmaydi.** Barcha doimiy
   ma'lumotlar PostgreSQL'da qoladi. Redis'dagi hamma narsa yo'qolsa,
   loyiha bironta ma'lumot yo'qotmaydi.

---

## 10. Kelgusi rivojlantirish

| № | Imkoniyat |
|---|---|
| 1 | Kitob sahifasidagi sharhlar ro'yxatini keshlash |
| 2 | Sotuvchi kabinetidagi statistikani keshlash |
| 3 | Kirish sahifasiga chegara qo'yish (parol tanlash urinishlariga qarshi) |
| 4 | Celery + Redis: og'ir ishlarni fon rejimiga o'tkazish (ommaviy email) |
| 5 | Kesh samaradorligini o'lchash (nechta so'rov keshdan berildi) |

---

*Hujjat oxiri*
