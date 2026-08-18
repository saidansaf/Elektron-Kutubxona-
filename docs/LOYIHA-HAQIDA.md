# ELEKTRON KUTUBXONA

## Loyiha haqida to'liq ma'lumot

---

| | |
|---|---|
| **Loyiha nomi** | Elektron Kutubxona |
| **Turi** | Elektron kitoblar oldi-sotdi platformasi (marketplace) |
| **Ishlab chiquvchi** | Saidansaf |
| **Repozitoriya** | https://github.com/saidansaf/Elektron-kitoblar |
| **Dasturlash tili** | Python 3.11 |
| **Asosiy freymvork** | Django 5.2 |
| **Texnologiya** | Python · Django · DRF · PostgreSQL · Redis |

---

# 1. Loyiha nima qiladi

Bu sayt **elektron kitoblarni sotish va sotib olish** uchun mo'ljallangan.
Oddiy qilib aytganda — kitoblar do'koni, lekin qog'oz kitoblar emas, PDF
kitoblar sotiladi.

Saytda ikki tomon bor:

**Sotuvchi** o'z kitobini joylashtiradi. U kitobning nomini, muallifini,
janrini, tilini, sahifalar sonini va narxini yozadi, PDF faylini va muqova
rasmini yuklaydi. Shundan keyin kitob katalogda paydo bo'ladi.

**Xaridor** katalogdan kitob qidiradi, uni sotib oladi va **saytning
o'zida o'qiydi** — hech qayerga yuklab olish shart emas. Kitobni yoqtirishi,
unga 1 dan 5 gacha yulduz qo'yishi va izoh yozishi mumkin.

Ular orasida **administrator** turadi: foydalanuvchilarni boshqaradi,
qoidabuzarni bloklaydi, sotuvchilarga pul to'laydi.

Pul harakati saytning ichida ketadi. Har bir foydalanuvchining **balansi**
bor: xaridor uni karta orqali to'ldiradi, kitob sotib olganda pul
balansidan yechilib sotuvchining balansiga o'tadi, sotuvchi esa yig'ilgan
pulni kartasiga chiqarib olish uchun so'rov yuboradi.

---

# 2. Qanday dasturlardan foydalanilgan

Bu bo'lim eng muhimi: **har bir texnologiya nima uchun kerakligi** aniq
yozilgan. Loyihada "shunchaki bor" degan narsa yo'q — har biri aniq
vazifani bajaradi.

## 2.1. Python 3.11 — dasturlash tili

Butun loyiha shu tilda yozilgan. Python tanlangani bejiz emas: veb-saytlar
uchun tayyor kutubxonalari juda ko'p va kod o'qishga oson.

Loyihadagi Python kodi: **71 ta fayl, ~4 800 qator**.

## 2.2. Django 5.2 — asosiy freymvork

Django — bu veb-sayt yozish uchun tayyor "skelet". Usiz har bir saytda bir
xil ishni qaytadan yozishga to'g'ri kelardi.

Django loyihada quyidagilarni bajaradi:

| Vazifa | Tushuntirish |
|---|---|
| **URL boshqaruvi** | Qaysi manzil ochilganda qaysi kod ishlashini belgilaydi. Loyihada 66 ta manzil bor |
| **ORM** | Ma'lumotlar bazasi bilan SQL yozmasdan ishlash. `Book.objects.filter(...)` yozasiz, Django uni SQL ga aylantiradi |
| **Migratsiyalar** | Modelni o'zgartirsangiz, bazadagi jadvalni ham avtomatik o'zgartiradi |
| **Shablonlar** | HTML ichida sikl va shart yozish imkoni |
| **Formalar** | Foydalanuvchi kiritgan ma'lumotni tekshirish (masalan, karta raqami to'g'rimi) |
| **Autentifikatsiya** | Ro'yxatdan o'tish, kirish, chiqish, parolni tiklash |
| **Admin panel** | Barcha ma'lumotlarni ko'rish va tahrirlash uchun tayyor interfeys |
| **Xavfsizlik** | CSRF himoyasi, SQL-inyeksiyadan himoya, parollarni shifrlash |
| **Ko'p tillilik** | Saytni bir necha tilga tarjima qilish tizimi |

## 2.3. Django REST Framework 3.17 — API uchun

Sayt odamlar uchun HTML sahifa beradi. Lekin agar kelajakda **mobil ilova**
yozilsa, unga HTML kerak emas — unga toza ma'lumot kerak.

DRF shuning uchun ishlatilgan: u bir xil ma'lumotni **JSON** ko'rinishida
beradi. Masalan `/api/books/` manziliga murojaat qilsangiz, kitoblar
ro'yxati dastur o'qiy oladigan formatda keladi.

Loyihada DRF orqali 5 ta bo'lim ochilgan: kitoblar, mualliflar, janrlar,
sharhlar va o'z xaridlari.

## 2.4. django-filter 26.1 — filtrlash

Katalogda kitoblarni tilga, janrga, muallifga va narx oralig'iga qarab
saralash kerak. Buni qo'lda yozsa ham bo'lardi, lekin django-filter buni
qisqa va xatosiz qiladi.

## 2.5. PostgreSQL 16 — ma'lumotlar bazasi

Barcha ma'lumot shu yerda saqlanadi: foydalanuvchilar, kitoblar, xaridlar,
sharhlar, balanslar.

PostgreSQL tanlangani sabablari:

- **Ishonchli** — pul bilan bog'liq amallar uchun muhim. Xarid paytida pul
  bir hisobdan yechilib ikkinchisiga qo'shiladi; agar o'rtada nimadir
  buzilsa, PostgreSQL ikkala amalni ham bekor qiladi (tranzaksiya)
- **Kuchli** — murakkab hisob-kitoblarni (masalan, sotuvchining daromadi)
  bazaning o'zida bajaradi
- **Bepul va ochiq kodli**

**Muhim qulaylik:** loyiha **SQLite** bilan ham ishlaydi. SQLite —
o'rnatish talab qilmaydigan oddiy baza, u bitta fayldan iborat. Yangi
kompyuterda loyihani sinab ko'rish uchun PostgreSQL o'rnatib o'tirmasdan
darhol ishga tushirsa bo'ladi. `.env` faylidagi bitta qator buni
hal qiladi.

## 2.6. psycopg2 2.9 — PostgreSQL drayveri

Python bilan PostgreSQL o'rtasidagi ko'prik. Django'ning o'zi PostgreSQL
bilan gaplashishni bilmaydi — shu kutubxona orqali gaplashadi.

## 2.7. HTML5, CSS3, JavaScript — sayt ko'rinishi

**HTML** — sahifaning tuzilishi (33 ta shablon fayl).

**CSS** — ko'rinish va dizayn (2 555 qator). Bu yerda tayyor kutubxona
(Bootstrap kabi) **ishlatilmagan** — barcha dizayn qo'lda yozilgan. Shu
sababli sayt boshqa saytlarga o'xshamaydi.

CSS'da ishlatilgan zamonaviy imkoniyatlar:

- **CSS o'zgaruvchilari** — ranglar bir joyda belgilanadi, shuning uchun
  qorong'i temaga o'tish oson
- **Flexbox va Grid** — elementlarni joylashtirish
- **Gradientlar** — chiroyli rangli o'tishlar
- **Moslashuvchan (responsive)** — telefonda ham, kompyuterda ham to'g'ri
  ko'rinadi

**JavaScript** — brauzerda ishlaydigan kod (60 qator). U kam ishlatilgan
va ataylab shunday: sahifalarning aksariyati server tomonida yasaladi, bu
esa saytni tez va soddaroq qiladi.

## 2.8. PDF.js 4.6 — kitobni brauzerda o'qish

Bu Mozilla (Firefox brauzerining ishlab chiquvchisi) yozgan kutubxona. U
PDF faylni brauzer ichida ochib beradi.

Uning yordamida xaridor kitobni **yuklab olmasdan**, saytning o'zida
o'qiydi: sahifalarni varaqlaydi, kattalashtiradi, butun ekranga o'tadi.

Kutubxona loyihaning ichida saqlanadi (`static/vendor/pdfjs/`), ya'ni
internetdan yuklab olinmaydi — bu tezroq va ishonchliroq.

## 2.9. Redis — kesh (ixtiyoriy)

Redis — ma'lumotni **tezkor xotirada** saqlaydigan dastur. Loyihada u
ma'lumotlar bazasi sifatida emas, **kesh** sifatida ishlatiladi.

Muammo shunda ediki: bosh sahifa har ochilganda bir xil ish qaytadan
bajarilardi — eng yangi kitoblar, ularning baholari, yoqtirishlari. Bu 18
ta baza so'rovini talab qilardi.

Redis natijani eslab qoladi va keyingi safar tayyor holda beradi:

| Sahifa | Redis'siz | Redis bilan |
|---|---|---|
| Bosh sahifa | 18 ta so'rov, 364 ms | **0 ta so'rov, 4 ms** |
| Katalog | 10 ta so'rov | 3 ta so'rov |

**Redis majburiy emas.** O'rnatilmagan bo'lsa loyiha xuddi avvalgidek
ishlayveradi — shunchaki sekinroq. Bu ataylab shunday qilingan: loyihani
istalgan kompyuterda qo'shimcha dastur o'rnatmasdan ishga tushirish kerak.

## 2.10. Pillow 12 — rasmlar bilan ishlash

Kitob muqovalari va profil rasmlari uchun. Yuklangan faylning haqiqatan
rasm ekanini tekshiradi va o'lchamini o'qiydi.

## 2.11. openpyxl 3.1 — Excel hisobotlari

Sotuvchi o'z kitoblari va savdo hisobotini **Excel faylida** yuklab olishi
mumkin. Shu kutubxona `.xlsx` faylini yasaydi.

## 2.12. reportlab 5.0 — PDF hisobotlari

Xuddi shu ma'lumotni PDF ko'rinishida ham beradi.

## 2.13. python-dotenv 1.2 — maxfiy sozlamalar

Parollar, API kalitlari va baza ma'lumotlari kod ichida yozilmasligi kerak
— aks holda ular GitHub'ga tushib, hammaga ko'rinib qoladi.

Ular `.env` deb nomlangan alohida faylda saqlanadi. Bu fayl git'ga
tushmaydi. python-dotenv shu fayldan sozlamalarni o'qiydi.

## 2.14. Sun'iy intellekt (AI)

Loyihada AI yordamchi bor. U uchta bepul provayderdan biri orqali ishlaydi:

| Provayder | Izoh |
|---|---|
| **Google Gemini** | Bepul, saxiy limit |
| **Groq** | Bepul, juda tez |
| **OpenRouter** | Bepul modellar bor |

Kalit `.env` faylga qo'yiladi. Loyiha kalitning boshiga qarab provayderni
**o'zi aniqlaydi** — qo'lda tanlash shart emas.

Rasm generatsiyasi uchun **Pollinations** ishlatiladi — u umuman kalit
talab qilmaydi.

## 2.15. Open-Meteo — ob-havo

Saytda ob-havo sahifasi bor. Ma'lumot Open-Meteo xizmatidan olinadi — u
bepul va ro'yxatdan o'tishni talab qilmaydi.

---

# 3. Loyiha qanday tuzilgan

Loyiha uchta katta qismga (Django terminologiyasida — **ilova**) bo'lingan.
Har biri o'z ishi bilan shug'ullanadi.

```
Elektron-kitoblar/
│
├── config/              Umumiy sozlamalar va asosiy manzillar
│
├── apps/
│   ├── accounts/        Foydalanuvchilar
│   ├── books/           Kitoblar va savdo
│   └── core/            Bosh sahifa, AI, admin, kesh
│
├── templates/           HTML sahifalar (33 ta)
├── static/              CSS, JavaScript, PDF.js
├── locale/              Tarjimalar (uz / ru / en)
├── media/               Ochiq fayllar: muqovalar, avatarlar
├── private_media/       Pullik kitob PDF'lari (himoyalangan)
└── docs/                Hujjatlar
```

## 3.1. `accounts` — foydalanuvchilar

Kim saytga kirgani, uning roli, tili, temasi, balansi — hammasi shu yerda.

Bu ilovadagi jadvallar:

| Jadval | Nima saqlaydi |
|---|---|
| `User` | Foydalanuvchi: login, parol, rol, til, tema, balans, avatar |
| `TopUp` | Balansni to'ldirish tarixi |
| `Withdrawal` | Sotuvchining pul yechish so'rovlari |
| `AdminMessage` | Administrator yuborgan xabarlar |
| `MessageRead` | Kim qaysi xabarni o'qigani |

## 3.2. `books` — kitoblar va savdo

Loyihaning yuragi. Kitoblar, xaridlar, sharhlar — hammasi shu yerda.

| Jadval | Nima saqlaydi |
|---|---|
| `Book` | Kitob: nomi, narxi, tili, sahifalari, PDF fayli, muqovasi |
| `Author` | Muallif: ismi, tarjimai holi, rasmi |
| `Genre` | Janr |
| `Purchase` | Xarid: kim, qaysi kitobni, qanchaga sotib olgani |
| `Review` | Sharh: baho (1–5 yulduz) va matn |
| `Reply` | Sharhga javob |
| `Like` | Kitobni yoqtirish |
| `ReviewLike`, `ReplyLike` | Izoh va javobni yoqtirish |
| `ReadingProgress` | Kitob qaysi sahifagacha o'qilgani |

## 3.3. `core` — umumiy qismlar

Boshqa ikkalasiga kirmagan narsalar: bosh sahifa, ob-havo, AI yordamchi,
administrator paneli, kesh va til/tema almashtirish.

---

# 4. Loyihaning barcha imkoniyatlari

## 4.1. Ro'yxatdan o'tish va rollar

Foydalanuvchi login, email va parol bilan ro'yxatdan o'tadi. Shundan keyin
**rolini tanlaydi**: sotuvchimi yoki sotib oluvchi. Rolni keyinchalik
sozlamalardan o'zgartirish mumkin.

Parolni unutgan bo'lsa — email orqali tiklaydi.

## 4.2. Uch til

Sayt **o'zbek, rus va ingliz** tillarida ishlaydi. Til header'dagi
tugmadan yoki sozlamalardan almashtiriladi va foydalanuvchi profilida
saqlanadi.

Jami **405 ta matn** tarjima qilingan.

Muhim nozik jihat: **kitobning tili** va **saytning tili** — ikki xil
narsa. Sayt inglizcha bo'lishi, lekin unda o'zbekcha kitob sotilishi
mumkin. Kitobning tilini sotuvchi belgilaydi.

## 4.3. Ikki tema

**Yorug'** va **qorong'i** rejim. Tanlov profilda saqlanadi, ya'ni boshqa
qurilmadan kirsangiz ham o'sha tema qoladi.

## 4.4. Katalog

Barcha sotuvdagi kitoblar. Qidirish (nom yoki muallif bo'yicha) va
filtrlash (til, janr, muallif, narx oralig'i) mumkin. Sahifada 9 tadan
kitob ko'rsatiladi.

## 4.5. Kitob sahifasi

To'liq ma'lumot: muqova, tavsif, sahifalar soni, til, nashr yili, sotuvchi,
o'rtacha baho va barcha sharhlar.

## 4.6. Yoqtirish, baholash va izohlar

Bu bo'limda muhim qoida bor: **kitobni sotib olish shart emas**. Ro'yxatdan
o'tgan har qanday foydalanuvchi kitobni yoqtirishi, baholashi va izoh
yozishi mumkin.

Izohlar quyidagicha tuzilgan:

```
👤 Foydalanuvchi nomi          ★★★★☆
   Izoh matni shu yerda...                    ❤ 5
   │
   └─ 👤 Boshqa foydalanuvchi
      Javob matni...                          ❤ 2
```

Javobga javob yozib **bo'lmaydi** — muhokama bir daraja bilan
chegaralangan, shunda u tarqalib ketmaydi.

## 4.7. Kitob sotib olish

To'lov **faqat karta orqali** — sayt elektron kitoblar sotgani uchun "olib
ketish" degan variant yo'q.

To'lov sahifasida karta raqami, amal qilish muddati va uy manzili
so'raladi. **Karta ma'lumotlari saqlanmaydi** — chek uchun faqat oxirgi 4
raqam qoladi.

Pul xaridorning balansidan yechilib sotuvchining balansiga o'tadi. Balans
yetmasa, xarid amalga oshmaydi.

Bir kitobni bir foydalanuvchi faqat bir marta sotib oladi.

## 4.8. Kitobni brauzerda o'qish

Sotib olingan kitob saytning o'zida ochiladi:

- sahifalarni varaqlash va istalgan sahifaga o'tish
- kattalashtirish / kichraytirish
- butun ekran rejimi
- klaviatura bilan boshqarish (← → PageUp PageDown Home End)

**To'xtagan joyingiz avtomatik saqlanadi.** Ertaga boshqa kompyuterdan
kirsangiz ham kitob o'sha sahifadan ochiladi. "Mening kutubxonam"da necha
foiz o'qilgani va "Davom ettirish" tugmasi ko'rinadi.

## 4.9. Pullik kitoblar qanday himoyalangan

Bu texnik jihatdan eng nozik joy.

Odatda yuklangan fayllar `media/` papkasida turadi va ular internetga
**ochiq** beriladi. Ya'ni manzilni bilgan har kim pullik kitobni tekinga
yuklab olishi mumkin bo'lardi.

Shuning uchun kitob PDF'lari alohida, **yopiq papkada** saqlanadi va faqat
tekshiruvdan o'tgandan keyin beriladi:

| Kim | Natija |
|---|---|
| Kitobni sotib olgan xaridor | ✅ ochadi |
| Kitobning sotuvchisi | ✅ ochadi |
| Administrator | ✅ ochadi |
| Boshqa hamma | ❌ 404 (fayl yo'q, deb ko'rsatiladi) |

`403` ("ruxsat yo'q") emas, `404` ("topilmadi") qaytariladi — begona odam
kitobning fayli borligini ham bilmasligi kerak.

REST API ham faylga havola bermaydi: tashqaridan faqat "fayl bor" degan
belgi ko'rinadi.

## 4.10. Balansni to'ldirish

Xaridor karta orqali balansini to'ldiradi. Eng kam summa — 1 000 so'm,
eng ko'pi — 10 000 000 so'm. To'ldirishlar tarixi saqlanadi.

## 4.11. Sotuvchi kabineti

Sotuvchi uchun alohida sahifa:

- **umumiy daromad**, sotilgan nusxalar va xaridorlar soni
- **oxirgi 30 kunlik savdo grafigi**
- har bir kitob bo'yicha: narxi, nechta sotilgani, qancha daromad
  keltirgani, reytingi, yoqtirishlari
- oxirgi 10 ta sotuv
- savdo hisobotini **Excel** ga yuklash

## 4.12. Pul yechish

Sotuvchi yig'ilgan pulni kartasiga chiqarish uchun so'rov yuboradi.

So'rov yuborilishi bilan summa balansdan **ushlab qolinadi** — aks holda
bir pulni bir necha marta so'rash mumkin bo'lardi. Administrator so'rovni
tasdiqlaydi yoki izoh bilan rad etadi. Rad etilsa, pul balansga qaytariladi.

Bir vaqtda faqat bitta ko'rib chiqilmagan so'rov bo'lishi mumkin.

## 4.13. Administrator paneli

Bosh sahifa manzili oxiriga **`#admin`** qo'shilsa, maxfiy kirish
sahifasiga yo'naltiradi. Bu manzil hech qayerda ko'rsatilmagan.

Administrator nima qila oladi:

- statistikani ko'rish (foydalanuvchilar, kitoblar, mualliflar, xaridlar)
- foydalanuvchini **bloklash** (sabab ko'rsatib) yoki blokdan chiqarish
- hisobni **o'chirish**
- **shaxsiy xabar** yuborish — foydalanuvchi saytga kirganda ko'radi
- barchaga **e'lon** tarqatish
- **yangi parol** belgilash
- pul yechish so'rovlarini ko'rib chiqish

> **Parol haqida.** Foydalanuvchining mavjud parolini ko'rsatib bo'lmaydi.
> Django parolni bir tomonlama shifrlab saqlaydi va uni asl holiga
> qaytarish matematik jihatdan imkonsiz. Shuning uchun uning o'rniga
> yangi parol belgilash qo'yilgan.

## 4.14. AI yordamchi

AI quyidagilarni qila oladi:

- kitoblar, mualliflar va janrlar haqida suhbatlashish
- kitob tanlashda maslahat berish
- sotuvchi uchun **kitob tavsifini yozib berish**
- muqova uchun **rasm generatsiya qilish**
- saytdan qanday foydalanishni tushuntirish

**AI saytga kitob qo'sha olmaydi** — bu faqat sotuvchining huquqi.

Bepul API kalitlarining limiti bor, shuning uchun har bir foydalanuvchi
uchun **soatiga 30 ta xabar va 10 ta rasm** chegarasi qo'yilgan. Qolgan
so'rovlar soni ekranda ko'rinib turadi.

## 4.15. Ob-havo

Alohida sahifa: joriy ob-havo, 24 soatlik va haftalik prognoz, harorat
grafigi. Joylashuv brauzerdan so'raladi, ruxsat berilmasa Toshkent
ko'rsatiladi.

## 4.16. Hisobotlar

Kitoblar va mualliflar ro'yxatini **Excel** yoki **PDF** ga chiqarish
mumkin. Sotuvchi uchun alohida savdo hisoboti bor.

## 4.17. REST API

`/api/` manzilida. Kelajakda mobil ilova yozilsa, u shu API orqali
ma'lumot oladi.

---

# 5. Sifat nazorati

## 5.1. Avtomatik testlar

Loyihada **55 ta test** bor. Ular asosan eng xavfli joylarni tekshiradi:

| Nima tekshiriladi | Nechta test |
|---|---|
| Kitob fayliga kim kira olishi | 9 |
| Pul yechish so'rovi va uni ko'rib chiqish | 11 |
| Kesh, uning yangilanishi va kalitlar | 9 |
| Sotuvchi kabinetidagi hisob-kitob | 5 |
| Redis o'chganda saytning ishlashi | 4 |
| O'qish holatini saqlash | 4 |
| Kontent versiyasi | 3 |
| AI so'rovlari chegarasi | 3 |
| Balansni to'ldirish | 2 |
| Xarid va pul o'tkazish | 2 |
| API faylga havola bermasligi | 1 |
| **Jami** | **55** |

Ishga tushirish: `python manage.py test`

## 5.2. Tashxis buyruqlari

Nimadir ishlamay qolsa, muammoni **o'zi topib beradigan** uchta buyruq
yozilgan:

```
python manage.py check_db      # baza: ulanish, jadvallar, ma'lumotlar
python manage.py check_ai      # AI: kalit, provayder, sinov so'rovi
python manage.py check_cache   # kesh: Redis, versiya, chegara
```

Ular xatoni topib, uni qanday tuzatishni ham aytadi.

## 5.3. Xavfsizlik choralari

| Chora | Tushuntirish |
|---|---|
| Parollar shifrlangan | PBKDF2 algoritmi bilan, ochiq saqlanmaydi |
| CSRF himoyasi | Boshqa saytdan soxta so'rov yuborib bo'lmaydi |
| SQL-inyeksiyadan himoya | Django ORM buni o'zi ta'minlaydi |
| XSS himoyasi | Shablonlar HTML belgilarini avtomatik zararsizlantiradi |
| Maxfiy ma'lumot ajratilgan | Parollar va kalitlar `.env` da, git'ga tushmaydi |
| Rollar nazorati | Sotuvchi faqat o'z kitobini tahrirlaydi |
| Fayl turini tekshirish | Kitob fayli faqat PDF bo'lishi mumkin |
| Pullik kontent yopiq | PDF faqat xaridni tekshirgandan keyin beriladi |
| Karta saqlanmaydi | Faqat oxirgi 4 raqam qoladi |

---

# 6. Loyiha raqamlarda

| Ko'rsatkich | Qiymat |
|---|---|
| Python kodi | ~4 800 qator, 71 ta fayl |
| HTML shablonlar | ~2 500 qator, 33 ta fayl |
| CSS | ~2 550 qator |
| JavaScript (o'z kodimiz) | 60 qator |
| Ma'lumotlar bazasi jadvallari | 15 ta |
| Sayt manzillari | 66 ta |
| Avtomatik testlar | 55 ta |
| Tarjima qilingan matnlar | 405 ta |
| Qo'llab-quvvatlanadigan tillar | 3 ta (uz, ru, en) |
| Tashqi kutubxonalar | 9 ta |

---

# 7. Qanday ishga tushiriladi

## 7.1. Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env

python manage.py migrate
python manage.py seed_admin
python manage.py runserver
```

Sayt: http://127.0.0.1:8000/

## 7.2. Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env

python manage.py migrate
python manage.py seed_admin
python manage.py runserver
```

## 7.3. Nima o'rnatish kerak

**Majburiy:** faqat Python 3.11 va Git.

**Ixtiyoriy:**

| Dastur | Nima uchun | Bo'lmasa nima bo'ladi |
|---|---|---|
| PostgreSQL | Asosiy baza | SQLite ishlatiladi, hamma narsa ishlaydi |
| Redis | Kesh | Xotiradagi kesh ishlatiladi, sekinroq |
| AI kaliti | AI yordamchi | AI sahifasi ogohlantirish ko'rsatadi |
| SMTP (email) | Parolni tiklash | Havola ekranda ko'rsatiladi |

Ya'ni **hech narsa o'rnatmasdan** ham loyihani to'liq ishga tushirish
mumkin. Bu ataylab shunday qilingan.

---

# 8. Nimalar qilinmagan va nima uchun

Ochiq aytish kerak — bu o'quv loyihasi va unda ataylab qilinmagan narsalar
bor:

**1. Haqiqiy to'lov tizimi ulanmagan.** Payme, Click yoki Uzcard bilan
integratsiya yo'q. Karta raqami faqat formatiga qarab tekshiriladi, pul
esa saytning ichki balansi orqali harakatlanadi. Haqiqiy integratsiya
uchun bank bilan shartnoma va litsenziya kerak.

**2. Parolni ko'rsatish imkoni yo'q.** Buni qilib bo'lmaydi — Django
parolni qaytarib bo'lmaydigan tarzda shifrlaydi. Buning o'rniga
administrator yangi parol belgilay oladi.

**3. Kitob nusxalanishidan to'liq himoya yo'q.** Sotib olgan odam PDF'ni
yuklab olib, uni boshqalarga bera oladi. Bunga qarshi DRM tizimi kerak
bo'lardi — bu alohida katta ish va aksariyat kitob do'konlarida ham u yo'q.

---

# 9. Kelgusida qo'shish mumkin bo'lgan narsalar

| № | Imkoniyat |
|---|---|
| 1 | Istaklar ro'yxati (wishlist) |
| 2 | Haqiqiy to'lov tizimlari (Payme, Click) |
| 3 | AI asosida kitob tavsiya qilish |
| 4 | Mobil ilova uchun token autentifikatsiyasi |
| 5 | Kitob ichidan matn qidirish |
| 6 | Email va push bildirishnomalar |
| 7 | Bulutli hostingga joylashtirish |

---

# 10. Qo'shimcha hujjatlar

| Fayl | Mazmuni |
|---|---|
| `README.md` | O'rnatish va foydalanish qo'llanmasi |
| `docs/TEXNIK-TOPSHIRIQ.md` | Rasmiy texnik topshiriq (talablar ro'yxati) |
| `docs/TZ-KESH-VA-CHEGARA.md` | Kesh quyi tizimi uchun alohida TZ |
| `docs/LOYIHA-HAQIDA.md` | Shu hujjat |

---

*Hujjat oxiri*
