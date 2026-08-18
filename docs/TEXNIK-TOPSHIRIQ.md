# TEXNIK TOPSHIRIQ (TZ)

## "Elektron Kutubxona" — elektron kitoblar oldi-sotdi platformasi

---

### Hujjat haqida

| Maydon | Qiymat |
|---|---|
| Loyiha nomi | Elektron Kutubxona (Elektron kitoblar marketplace) |
| Hujjat turi | Texnik topshiriq (TZ) |
| Versiya | 1.3 |
| Ishlab chiquvchi | Saidansaf |
| Repozitoriya | https://github.com/saidansaf/Elektron-kitoblar |
| Texnologiya | Python / Django / Django REST Framework / PostgreSQL |

---

## 1. Umumiy qoidalar

### 1.1. Loyihaning maqsadi

Elektron kitoblarni onlayn sotish va sotib olish uchun veb-platforma yaratish.
Platforma ikki tomonni bog'laydi: kitob **sotuvchilari** (mualliflar, nashriyotlar)
va kitob **xaridorlari**. Sotuvchi o'z elektron kitobini PDF ko'rinishida
joylashtiradi va narx belgilaydi, xaridor esa ichki hamyon balansi orqali
uni sotib oladi, o'qiydi, baholaydi va sharh qoldiradi.

### 1.2. Loyihaning vazifalari

1. Foydalanuvchilarni ro'yxatdan o'tkazish va rollarga ajratish.
2. Kitoblar katalogini yuritish, qidiruv va filtrlash imkonini berish.
3. Ichki to'lov (hamyon) tizimi orqali xaridni amalga oshirish.
4. Kitoblarni baholash (1–5 yulduz), izohlash va muhokama qilish muhitini yaratish.
5. Uch tilli (o'zbek, rus, ingliz) va ikki temali (yorug'/qorong'i) interfeysni ta'minlash.
6. Administrator uchun foydalanuvchilarni va kontentni boshqarish vositalarini berish.
7. Hisobotlarni Excel va PDF formatlarida eksport qilish.
8. Sun'iy intellekt (AI) yordamchisini integratsiya qilish.
9. Tashqi ilovalar uchun REST API taqdim etish.

### 1.3. Atamalar va qisqartmalar

| Atama | Ta'rifi |
|---|---|
| **Sotuvchi** | Saytga kitob joylashtiruvchi va sotuvchi foydalanuvchi |
| **Xaridor** | Kitob sotib oluvchi foydalanuvchi |
| **Administrator** | Tizimning to'liq boshqaruv huquqiga ega foydalanuvchi |
| **Balans (hamyon)** | Foydalanuvchining tizim ichidagi pul hisobi |
| **Katalog** | Sotuvdagi barcha kitoblar ro'yxati |
| **Sharh (Review)** | Kitobga qoldirilgan baho va matnli izoh |
| **Javob (Reply)** | Sharhga yozilgan javob (faqat bir daraja) |
| **Broadcast** | Administratorning barcha foydalanuvchilarga e'loni |
| **TZ** | Texnik topshiriq |
| **API** | Application Programming Interface |
| **DRF** | Django REST Framework |

---

## 2. Foydalanuvchi rollari

Tizimda **uch xil rol** mavjud. Foydalanuvchi ro'yxatdan o'tgach, birinchi
kirishda o'z rolini tanlaydi va keyinchalik Sozlamalar bo'limidan uni
o'zgartirishi mumkin.

### 2.1. Sotib oluvchi (Buyer)

- Katalogni ko'rish, qidirish va filtrlash
- Kitob sahifasini ochish, tavsif va sharhlarni o'qish
- Hisob balansini karta orqali to'ldirish
- Kitob sotib olish
- "Mening kutubxonam" bo'limida sotib olingan kitoblarni ko'rish
- Kitobni **brauzerda o'qish** (yuklab olmasdan), o'qilgan sahifa saqlanadi
- Kitob PDF'ini yuklab olish
- Kitobni yoqtirish (like), 1–5 yulduz baho va izoh qoldirish
- Boshqalarning izohiga javob yozish, izoh va javoblarni yoqtirish
- AI yordamchi bilan suhbatlashish

### 2.2. Sotuvchi (Seller)

Xaridorning barcha imkoniyatlaridan tashqari:

- Yangi kitob qo'shish (nom, muallif, janr, til, sahifalar soni, narx, tavsif, muqova, PDF fayl, nashr yili)
- O'z kitobini tahrirlash va o'chirish
- Yangi muallif qo'shish
- "Mening kitoblarim" bo'limida o'z kitoblarini boshqarish
- **Sotuvchi kabineti**: daromad, sotuvlar, xaridorlar, 30 kunlik grafik
- Balansdan kartaga **pul yechish so'rovi** yuborish
- Kitoblar va mualliflar ro'yxatini Excel/PDF ga eksport qilish
- AI yordamida kitob tavsifini yozdirish va muqova uchun rasm generatsiya qilish

### 2.3. Administrator

- Statistika paneli: foydalanuvchilar, kitoblar, mualliflar, xaridlar soni
- Foydalanuvchilar ro'yxati va har biri bo'yicha batafsil kartochka
- Foydalanuvchini **bloklash / blokdan chiqarish** (sabab ko'rsatgan holda)
- Foydalanuvchi hisobini **o'chirish**
- Foydalanuvchiga **shaxsiy xabar** yuborish (u saytga kirganda ko'radi)
- Barcha foydalanuvchilarga **e'lon (broadcast)** tarqatish
- Foydalanuvchiga **yangi parol belgilash**
- To'liq Django admin paneliga kirish

> **Muhim cheklov.** Foydalanuvchining mavjud parolini ko'rsatish **texnik
> jihatdan imkonsiz**: Django parollarni bir tomonlama shifrlab (PBKDF2 hash)
> saqlaydi va uni asl ko'rinishga qaytarish mumkin emas. Shu sababli TZ ga
> "parolni ko'rish" o'rniga **"yangi parol belgilash"** funksiyasi kiritilgan:
> administrator kiritgan yangi parol saqlanadi va ekranda bir marta ko'rsatiladi.

---

## 3. Funksional talablar

### 3.1. Autentifikatsiya va ro'yxatdan o'tish

| № | Talab |
|---|---|
| F-1.1 | Foydalanuvchi login, email va parol bilan ro'yxatdan o'tadi |
| F-1.2 | Ro'yxatdan o'tgach avtomatik rol tanlash sahifasiga yo'naltiriladi |
| F-1.3 | Login/parol orqali tizimga kirish |
| F-1.4 | Tizimdan chiqish |
| F-1.5 | Parolni unutganda email orqali tiklash (Django xavfsiz token tizimi) |
| F-1.6 | SMTP sozlanmagan bo'lsa, DEBUG rejimida tiklash havolasi ekranda ko'rsatiladi |
| F-1.7 | Bloklangan foydalanuvchi tizimga kira olmaydi, sabab ko'rsatiladi |

### 3.2. Maxfiy administrator kirishi

| № | Talab |
|---|---|
| F-2.1 | Bosh sahifa manzili oxiriga `#admin` qo'shilsa, maxfiy kirish sahifasiga yo'naltiradi |
| F-2.2 | Manzil: `/boshqaruv-panel/kirish/` |
| F-2.3 | Login/parol `.env` faylidagi `ADMIN_USERNAME` / `ADMIN_PASSWORD` orqali beriladi |
| F-2.4 | Standart Django admin paneli taxmin qilib bo'lmaydigan manzilda: `/django-boshqaruv-x9f2/` |
| F-2.5 | Administrator hisobi `python manage.py seed_admin` buyrug'i bilan yaratiladi |

### 3.3. Profil va sozlamalar

| № | Talab |
|---|---|
| F-3.1 | Rolni o'zgartirish (sotuvchi ↔ sotib oluvchi) |
| F-3.2 | Interfeys mavzusini tanlash: yorug' / qorong'i |
| F-3.3 | Interfeys tilini tanlash: o'zbekcha / русский / english |
| F-3.4 | Profil rasmi (avatar) yuklash |
| F-3.5 | Telefon raqamini kiritish |
| F-3.6 | O'zi haqida qisqacha ma'lumot (bio) yozish |
| F-3.7 | Joriy balansni ko'rish va to'ldirish tugmasi |
| F-3.8 | Administrator bilan Telegram orqali bog'lanish havolasi |
| F-3.9 | Header'dagi dumaloq avatar tugmasi ostida tez menyu: mavzu, til, sozlamalar, chiqish |

### 3.4. Kitoblar katalogi

| № | Talab |
|---|---|
| F-4.1 | Barcha sotuvdagi kitoblar ro'yxati (sahifalab chiqarish) |
| F-4.2 | Kitob nomi va muallif bo'yicha qidiruv |
| F-4.3 | Filtrlar: til, janr, muallif, narx oralig'i |
| F-4.4 | Kitob kartochkasida: muqova, nom, muallif, narx, o'rtacha baho, yoqtirishlar soni |
| F-4.5 | Kitob sahifasida to'liq ma'lumot: tavsif, sahifalar soni, til, nashr yili, sotuvchi |

### 3.5. Kitob boshqaruvi (sotuvchi uchun)

| № | Talab |
|---|---|
| F-5.1 | Kitob qo'shish formasi |
| F-5.2 | Kitob fayli **faqat PDF** formatida qabul qilinadi (validator bilan cheklangan) |
| F-5.3 | Muqova rasmi yuklash |
| F-5.4 | Kitob tilini sotuvchining o'zi belgilaydi (interfeys tilidan mustaqil) |
| F-5.5 | Kitobni tahrirlash va o'chirish — faqat o'z kitobini |
| F-5.6 | Kitobni sotuvdan olib qo'yish (`is_active` bayrog'i) |
| F-5.7 | Yangi muallif qo'shish (ism, tarjimai hol, tug'ilgan sana, rasm) |

### 3.6. Xarid va to'lov

| № | Talab |
|---|---|
| F-6.1 | Xarid **faqat karta orqali** amalga oshiriladi |
| F-6.2 | "Olib ketish" (pickup) usuli **yo'q** — sayt elektron kitoblarga mo'ljallangan |
| F-6.3 | To'lov formasida: karta raqami, amal qilish muddati, CVV, **uy manzili** |
| F-6.4 | Karta ma'lumotlari saqlanmaydi — chek uchun faqat oxirgi 4 raqam qoladi |
| F-6.5 | Xarid ichki hamyon balansidan yechiladi |
| F-6.6 | Balans yetmasa, foydalanuvchi to'ldirish sahifasiga yo'naltiriladi |
| F-6.7 | Bir kitobni bir foydalanuvchi faqat bir marta sotib oladi (`unique_together`) |
| F-6.8 | Xariddan so'ng kitob "Mening kutubxonam" bo'limiga tushadi |

### 3.7. Hisobni to'ldirish

| № | Talab |
|---|---|
| F-7.1 | Karta ma'lumotlari orqali balansni to'ldirish |
| F-7.2 | Minimal summa — 1 000 so'm, maksimal — 10 000 000 so'm |
| F-7.3 | To'ldirishlar tarixi saqlanadi va ko'rsatiladi |

### 3.8. Baholash, izohlar va muhokama

| № | Talab |
|---|---|
| F-8.1 | Kitobni yoqtirish (like) — **sotib olish shart emas** |
| F-8.2 | 1–5 yulduz baho qo'yish — **sotib olish shart emas** |
| F-8.3 | Matnli izoh yozish — **sotib olish shart emas** |
| F-8.4 | Bir foydalanuvchi bir kitobga bitta sharh qoldiradi |
| F-8.5 | Izoh tuzilishi: yuqorida foydalanuvchi nomi, ostida izoh matni, undan pastda javoblar |
| F-8.6 | Izohga javob yozish mumkin |
| F-8.7 | **Javobga javob yozib bo'lmaydi** — muhokama chuqurligi bir daraja bilan chegaralangan |
| F-8.8 | Izoh va javoblarni yoqtirish (like) mumkin |
| F-8.9 | Kitobning o'rtacha bahosi avtomatik hisoblanadi |

### 3.9. Administrator boshqaruvi

| № | Talab |
|---|---|
| F-9.1 | Statistika paneli: umumiy raqamlar |
| F-9.2 | Foydalanuvchilar ro'yxati va qidiruv |
| F-9.3 | Foydalanuvchi kartochkasi: profil, rol, balans, xaridlari, kitoblari |
| F-9.4 | Bloklash / blokdan chiqarish (sabab bilan) |
| F-9.5 | Hisobni o'chirish |
| F-9.6 | Shaxsiy xabar yuborish — foydalanuvchi saytga kirganda banner ko'rinishida ko'radi |
| F-9.7 | Barchaga e'lon (broadcast) tarqatish |
| F-9.8 | Yangi parol belgilash |
| F-9.9 | Xabar o'qilganligi belgilanadi va qayta ko'rsatilmaydi |

### 3.10. Sun'iy intellekt (AI) yordamchisi

| № | Talab |
|---|---|
| F-10.1 | Kitoblar, janrlar va mualliflar haqida suhbat |
| F-10.2 | Kitob tanlashda maslahat berish |
| F-10.3 | Sotuvchi uchun kitob tavsifini avtomatik yozib berish |
| F-10.4 | Muqova uchun rasm generatsiya qilish |
| F-10.5 | Saytdan qanday foydalanishni tushuntirish |
| F-10.6 | **AI saytga kitob qo'sha olmaydi** — bu faqat sotuvchining huquqi |
| F-10.7 | Suhbat tarixini tozalash imkoniyati |

**Qo'llab-quvvatlanadigan provayderlar** (kalit `.env` faylida saqlanadi):

| Provayder | Kalit olish manzili | Kalit prefiksi |
|---|---|---|
| Google Gemini | https://aistudio.google.com/apikey | `AIza`, `AQ.` |
| Groq | https://console.groq.com/keys | `gsk_` |
| OpenRouter | https://openrouter.ai/keys | `sk-or-` |
| Pollinations (rasm) | kalit talab qilmaydi | — |

Provayder kalit prefiksi bo'yicha **avtomatik aniqlanadi**.

### 3.11. Hisobotlarni eksport qilish

| № | Talab |
|---|---|
| F-11.1 | Kitoblar ro'yxatini **Excel (.xlsx)** ga eksport qilish |
| F-11.2 | Kitoblar ro'yxatini **PDF** ga eksport qilish |
| F-11.3 | Mualliflar ro'yxatini **Excel (.xlsx)** ga eksport qilish |
| F-11.4 | Mualliflar ro'yxatini **PDF** ga eksport qilish |

### 3.12. Ko'p tillilik va mavzular

| № | Talab |
|---|---|
| F-12.1 | Interfeys uch tilda: o'zbekcha (`uz`), ruscha (`ru`), inglizcha (`en`) |
| F-12.2 | Til Sozlamalardan yoki header'dagi tanlagichdan o'zgartiriladi |
| F-12.3 | Tanlangan til foydalanuvchi profilida saqlanadi |
| F-12.4 | Tarjimalar Django `gettext` mexanizmi orqali (`.po` / `.mo` fayllar) |
| F-12.5 | Kitobning tili — alohida maydon, interfeys tilidan mustaqil |
| F-12.6 | Ikki mavzu: yorug' va qorong'i; tanlov profilda saqlanadi |
| F-12.7 | Mavzu CSS o'zgaruvchilari va `data-theme` atributi orqali amalga oshiriladi |

---

### 3.13. Kitobni brauzerda o'qish

| № | Talab |
|---|---|
| F-13.1 | Sotib olingan kitob sayt ichida ochiladi, yuklab olish shart emas |
| F-13.2 | Uzluksiz varaqlash, sahifa raqamiga o'tish, oldingi/keyingi tugmalari |
| F-13.3 | Masshtabni o'zgartirish va butun ekran rejimi |
| F-13.4 | Klaviatura bilan boshqarish: ← → PageUp PageDown Home End |
| F-13.5 | Joriy sahifa avtomatik saqlanadi va boshqa qurilmada davom ettiriladi |
| F-13.6 | "Mening kutubxonam"da o'qilgan foiz va "Davom ettirish" tugmasi |
| F-13.7 | PDF.js loyiha ichida keladi — internetga chiqish talab qilinmaydi |

### 3.14. Pullik kontentni himoyalash

| № | Talab |
|---|---|
| F-14.1 | Kitob PDF fayli ochiq `media/` papkasida saqlanmaydi |
| F-14.2 | Fayl faqat xaridni tekshiradigan view orqali uzatiladi |
| F-14.3 | Faylni sotib olgan xaridor, kitob sotuvchisi va administrator ocha oladi |
| F-14.4 | Ruxsati yo'q foydalanuvchiga `404` qaytariladi (fayl borligi ham bilinmaydi) |
| F-14.5 | REST API faylga havola bermaydi — faqat `has_file` maydoni ko'rinadi |
| F-14.6 | Sotuvchi API orqali fayl yuklay oladi (yozish uchun ochiq, o'qish uchun yopiq) |

### 3.15. Sotuvchi kabineti

| № | Talab |
|---|---|
| F-15.1 | Umumiy daromad, sotilgan nusxalar soni, noyob xaridorlar soni |
| F-15.2 | Oxirgi 30 kunlik savdo grafigi (kunma-kun) |
| F-15.3 | Kitoblar kesimida jadval: narx, sotildi, daromad, reyting, yoqtirishlar |
| F-15.4 | Oxirgi 10 ta sotuv ro'yxati |
| F-15.5 | Savdo hisobotini Excel formatida yuklab olish |
| F-15.6 | Kabinetga faqat sotuvchi rolidagi foydalanuvchi kira oladi |

### 3.16. Pul yechish

| № | Talab |
|---|---|
| F-16.1 | Sotuvchi balansdan kartaga pul yechish so'rovini yuboradi |
| F-16.2 | Eng kam summa — 10 000 so'm |
| F-16.3 | Balansdan ko'p summa so'rab bo'lmaydi |
| F-16.4 | Summa so'rov yuborilishi bilan balansdan ushlab qolinadi |
| F-16.5 | Bir vaqtda faqat bitta ko'rib chiqilmagan so'rov bo'lishi mumkin |
| F-16.6 | Administrator so'rovni tasdiqlaydi yoki izoh bilan rad etadi |
| F-16.7 | Rad etilganda summa balansga qaytariladi |
| F-16.8 | So'rovlar tarixi sotuvchiga ham, administratorga ham ko'rinadi |

### 3.17. Keshlash (Redis)

> Bu quyi tizim uchun alohida, batafsil texnik topshiriq bor:
> `docs/TZ-KESH-VA-CHEGARA.md`

| № | Talab |
|---|---|
| F-17.1 | Redis `.env` dagi `REDIS_URL` orqali ulanadi |
| F-17.2 | `REDIS_URL` bo'sh bo'lsa xotiradagi kesh ishlatiladi — loyiha baribir ishlaydi |
| F-17.3 | Bosh sahifa va katalogdagi kitob kartochkalari keshlanadi |
| F-17.4 | Kesh kaliti interfeys tiliga bog'liq — tillar aralashib ketmaydi |
| F-17.5 | Katalogda har bir filtr kombinatsiyasi alohida keshlanadi |
| F-17.6 | Kitob, muallif, janr, sharh yoki yoqtirish o'zgarganda kesh yangilanadi |
| F-17.7 | Redis ulangan bo'lsa sessiyalar avval keshdan qidiriladi |
| F-17.8 | Redis o'chib qolsa sayt ishlashdan to'xtamaydi: ulanish xatosi "keshda topilmadi" sifatida qabul qilinadi |
| F-17.9 | `python manage.py check_cache` kesh holatini tekshiradi |

### 3.18. AI so'rovlari chegarasi

| № | Talab |
|---|---|
| F-18.1 | Har bir foydalanuvchi uchun oynada cheklangan miqdorda AI xabari |
| F-18.2 | Rasm generatsiyasi alohida hisoblanadi |
| F-18.3 | Chegaralar `.env` dan sozlanadi (standart: 30 xabar, 10 rasm / soat) |
| F-18.4 | Chegara tugaganda `429` kodi va tushunarli xabar qaytariladi |
| F-18.5 | Qolgan so'rovlar soni AI sahifasida ko'rinadi |
| F-18.6 | Kesh ishlamay qolsa chegara foydalanuvchini bloklamaydi |

## 4. Nofunksional talablar

### 4.1. Xavfsizlik

- Parollar Django'ning PBKDF2 algoritmi bilan hash qilinadi, ochiq saqlanmaydi
- Barcha formalarda CSRF himoyasi
- Maxfiy ma'lumotlar (`SECRET_KEY`, API kalitlar, DB paroli) `.env` faylida saqlanadi va repozitoriyaga tushmaydi (`.gitignore`)
- ORM orqali SQL-inyeksiyadan himoya
- Django shablonlari avtomatik HTML-ekranlash qiladi (XSS himoyasi)
- Rollar bo'yicha kirish nazorati: sotuvchi faqat o'z kitobini tahrirlaydi
- Yuklanadigan kitob fayli faqat PDF bo'lishi validator bilan tekshiriladi
- Karta ma'lumotlari saqlanmaydi
- Pullik kitob fayllari veb-server ko'rmaydigan papkada saqlanadi va faqat
  xaridni tekshirgandan keyin uzatiladi
- REST API pullik faylga havola bermaydi

### 4.2. Ishlash va kengaytiriluvchanlik

- Katalog sahifalab chiqariladi (API'da sahifada 12 ta yozuv)
- Ma'lumotlar bazasi indekslari va `select_related` / `prefetch_related` orqali so'rovlar optimizatsiyasi
- Modulli tuzilma: har bir funksional blok alohida Django ilovasi
- Bosh sahifa va katalog keshlanadi: keshdan berilgan bosh sahifa bazaga
  umuman so'rov yubormaydi (o'lchov: 18 ta so'rovdan 0 ga)
- AI so'rovlariga chegara — bitta foydalanuvchi tashqi xizmat limitini
  tugatib qo'ya olmaydi

### 4.3. Foydalanuvchi interfeysi

- Zamonaviy, gradientli, "yuqori darajali" dizayn — quruq oq fon va oddiy tugmalar emas
- Moslashuvchan (responsive) qatlam — kompyuter, planshet, telefon
- Segmentli tugmalar (segmented control) tanlov elementlari uchun
- Dumaloq avatar va ochiluvchi menyu
- Zamonaviy brauzerlar: Chrome, Firefox, Edge, Safari

### 4.4. O'rnatish va ekspluatatsiya

- Standart holda **SQLite** bilan darhol ishga tushadi (hech narsa sozlash shart emas)
- `.env` faylida bitta qatorni o'zgartirish orqali **PostgreSQL** ga o'tiladi
- Tayyor `.mo` tarjima fayllari loyiha ichida keladi — GNU gettext o'rnatish shart emas
- O'zini tekshiruvchi buyruqlar: `check_db` (baza) va `check_ai` (AI)
- Bazani avtomatik yaratuvchi buyruq: `setup_db`

---

## 5. Tizim arxitekturasi

### 5.1. Texnologiyalar to'plami

| Qatlam | Texnologiya |
|---|---|
| Dasturlash tili | Python 3.11+ |
| Veb-freymvork | Django 5.2 |
| API | Django REST Framework 3.15+ |
| Filtrlash | django-filter 24.3+ |
| Ma'lumotlar bazasi | PostgreSQL 16 (asosiy), SQLite (ishlab chiqish uchun) |
| DB drayveri | psycopg2-binary |
| Frontend | HTML5, CSS3 (CSS custom properties), Vanilla JavaScript |
| PDF o'quvchi | PDF.js 4.6 (loyiha ichida, tashqi CDN'siz) |
| Rasm bilan ishlash | Pillow |
| Excel eksport | openpyxl |
| PDF eksport | reportlab |
| Kesh (ixtiyoriy) | Redis 5+ (redis-py klienti) |
| Konfiguratsiya | python-dotenv |
| Ko'p tillilik | Django i18n (gettext) |

### 5.2. Loyiha tuzilishi

```
config/                 # Django sozlamalari va asosiy URL'lar
  settings.py           # Barcha konfiguratsiya
  urls.py               # Ildiz marshrutlar
apps/
  accounts/             # Foydalanuvchi, ro'yxatdan o'tish, sozlamalar, balans
  books/                # Kitob, Muallif, Janr, Sharh, Xarid, API, eksport
  core/                 # Bosh sahifa, mavzu/til, admin boshqaruvi, AI
    db/postgresql/      # PostgreSQL drayveri qobig'i (xatolarni o'qilishli qilish)
    management/commands # check_db, check_ai, setup_db
templates/              # HTML shablonlar
static/                 # CSS, JavaScript
locale/                 # uz / ru / en tarjimalar
media/                  # Yuklangan fayllar (muqovalar, PDF, avatarlar)
docs/                   # Hujjatlar
scripts/                # SQL skriptlar
```

### 5.3. Django ilovalari

| Ilova | Mas'uliyati |
|---|---|
| `apps.accounts` | Foydalanuvchi modeli, autentifikatsiya, rollar, sozlamalar, balans, parolni tiklash, administrator xabarlari |
| `apps.books` | Kitob, muallif, janr, xarid, sharh, javob, yoqtirish modellari; katalog; REST API; Excel/PDF eksport |
| `apps.core` | Bosh sahifa, mavzu va til almashtirish, kontekst protsessorlari, administrator boshqaruvi, AI xizmati, diagnostika buyruqlari |

---

## 6. Ma'lumotlar bazasi tuzilishi

### 6.1. `accounts_user` — Foydalanuvchi

Django'ning `AbstractUser` modelidan meros olingan (`AUTH_USER_MODEL`).

| Maydon | Turi | Izoh |
|---|---|---|
| `id` | integer | Birlamchi kalit |
| `username` | varchar(150) | Login, unikal |
| `email` | varchar | Elektron pochta |
| `password` | varchar | Hash qilingan parol |
| `first_name`, `last_name` | varchar | Ism, familiya |
| `role` | varchar(10) | `none` / `seller` / `buyer` |
| `theme` | varchar(5) | `light` / `dark` |
| `language` | varchar(5) | `uz` / `ru` / `en` |
| `phone` | varchar(20) | Telefon raqami |
| `avatar` | image | Profil rasmi |
| `balance` | decimal(12,2) | Hisob balansi |
| `bio` | text | O'zi haqida |
| `is_blocked` | boolean | Bloklanganmi |
| `blocked_reason` | varchar(255) | Bloklash sababi |
| `is_staff`, `is_superuser`, `is_active` | boolean | Django standart bayroqlari |
| `created_at` | datetime | Ro'yxatdan o'tgan vaqti |

### 6.2. `books_genre` — Janr

| Maydon | Turi | Izoh |
|---|---|---|
| `id` | integer | Birlamchi kalit |
| `name` | varchar(100) | Janr nomi, unikal |

### 6.3. `books_author` — Muallif

| Maydon | Turi | Izoh |
|---|---|---|
| `id` | integer | Birlamchi kalit |
| `full_name` | varchar(150) | To'liq ism |
| `bio` | text | Tarjimai hol |
| `birth_date` | date | Tug'ilgan sana |
| `photo` | image | Rasm |
| `created_by` | FK → User | Kim qo'shgan |
| `created_at` | datetime | Qo'shilgan vaqt |

### 6.4. `books_book` — Kitob

| Maydon | Turi | Izoh |
|---|---|---|
| `id` | integer | Birlamchi kalit |
| `title` | varchar(255) | Kitob nomi |
| `author` | FK → Author | Muallif |
| `genre` | FK → Genre | Janr (ixtiyoriy) |
| `seller` | FK → User | Sotuvchi |
| `language` | varchar(5) | Kitob tili |
| `pages` | integer | Sahifalar soni |
| `price` | decimal(10,2) | Narxi (so'm) |
| `description` | text | Tavsif |
| `cover` | image | Muqova rasmi |
| `file` | file | Kitob fayli — **faqat PDF** |
| `publish_year` | integer | Nashr yili |
| `is_active` | boolean | Sotuvda turibdimi |
| `created_at`, `updated_at` | datetime | Vaqt belgilari |

Hisoblanadigan xossalar: `average_rating`, `reviews_count`, `likes_count`.

### 6.5. `books_purchase` — Xarid

| Maydon | Turi | Izoh |
|---|---|---|
| `id` | integer | Birlamchi kalit |
| `buyer` | FK → User | Xaridor |
| `book` | FK → Book | Kitob |
| `price_paid` | decimal(10,2) | To'langan summa |
| `card_last4` | varchar(4) | Karta oxirgi 4 raqami |
| `address` | varchar(255) | Uy manzili |
| `purchased_at` | datetime | Xarid vaqti |

Cheklov: `unique_together (buyer, book)` — bir kitob bir marta sotib olinadi.

### 6.6. `books_review` — Sharh

| Maydon | Turi | Izoh |
|---|---|---|
| `id` | integer | Birlamchi kalit |
| `book` | FK → Book | Kitob |
| `buyer` | FK → User | Muallif |
| `rating` | smallint | 1–5 oralig'ida |
| `comment` | text | Izoh matni |
| `created_at` | datetime | Yozilgan vaqt |

Cheklov: `unique_together (book, buyer)`.

### 6.7. `books_reply` — Javob

| Maydon | Turi | Izoh |
|---|---|---|
| `id` | integer | Birlamchi kalit |
| `review` | FK → Review | Qaysi sharhga |
| `author` | FK → User | Kim yozgan |
| `text` | text | Javob matni |
| `created_at` | datetime | Vaqt |

Cheklov: javobga javob yozib bo'lmaydi (model darajasida `Reply` faqat `Review` ga bog'langan).

### 6.8. Yoqtirish jadvallari

| Jadval | Bog'lanish | Cheklov |
|---|---|---|
| `books_like` | Book ↔ User | `unique_together (book, user)` |
| `books_reviewlike` | Review ↔ User | `unique_together (review, user)` |
| `books_replylike` | Reply ↔ User | `unique_together (reply, user)` |

### 6.8a. `books_readingprogress` — O'qish holati

| Maydon | Turi | Izoh |
|---|---|---|
| `user` | FK → User | O'quvchi |
| `book` | FK → Book | Kitob |
| `page` | integer | Joriy sahifa |
| `total_pages` | integer | Kitobdagi jami sahifa |
| `updated_at` | datetime | Oxirgi o'qigan vaqti |

Cheklov: `unique_together (user, book)`. Hisoblanadigan xossalar: `percent`, `is_finished`.

### 6.8b. `accounts_withdrawal` — Pul yechish so'rovi

| Maydon | Turi | Izoh |
|---|---|---|
| `seller` | FK → User | Sotuvchi |
| `amount` | decimal(12,2) | Summa |
| `card_number` | varchar(25) | Karta raqami |
| `status` | varchar(10) | `pending` / `approved` / `rejected` |
| `comment` | varchar(255) | Administrator izohi |
| `created_at` | datetime | Yuborilgan vaqt |
| `processed_at` | datetime | Ko'rib chiqilgan vaqt |

### 6.9. `accounts_adminmessage` — Administrator xabari

| Maydon | Turi | Izoh |
|---|---|---|
| `recipient` | FK → User | Qabul qiluvchi (bo'sh = broadcast) |
| `sender` | FK → User | Yuboruvchi |
| `subject` | varchar(150) | Sarlavha |
| `body` | text | Matn |
| `is_broadcast` | boolean | Hammagami |
| `created_at` | datetime | Vaqt |

### 6.10. `accounts_messageread` — O'qilgan xabarlar

| Maydon | Turi | Izoh |
|---|---|---|
| `message` | FK → AdminMessage | Xabar |
| `user` | FK → User | Kim o'qigan |
| `read_at` | datetime | O'qilgan vaqt |

### 6.11. `accounts_topup` — Hisob to'ldirish

| Maydon | Turi | Izoh |
|---|---|---|
| `user` | FK → User | Foydalanuvchi |
| `amount` | decimal(12,2) | Summa |
| `card_last4` | varchar(4) | Karta oxirgi 4 raqami |
| `created_at` | datetime | Vaqt |

### 6.12. Munosabatlar sxemasi

```
User ──< Book >── Author ──< (Genre)
 │        │
 │        ├──< Purchase >── User
 │        ├──< Like >── User
 │        └──< Review >── User
 │                │
 │                ├──< ReviewLike >── User
 │                └──< Reply >── User
 │                        │
 │                        └──< ReplyLike >── User
 │
 ├──< TopUp
 ├──< AdminMessage
 └──< MessageRead
```

---

## 7. Sahifalar va marshrutlar (URL)

### 7.1. Umumiy sahifalar

| Manzil | Sahifa |
|---|---|
| `/` | Bosh sahifa |
| `/tema-almashtirish/` | Mavzuni almashtirish |
| `/til-almashtirish/` | Tilni almashtirish |

### 7.2. Hisob (`/hisobim/`)

| Manzil | Sahifa |
|---|---|
| `/hisobim/royxatdan-otish/` | Ro'yxatdan o'tish |
| `/hisobim/kirish/` | Kirish |
| `/hisobim/chiqish/` | Chiqish |
| `/hisobim/rol-tanlash/` | Rol tanlash |
| `/hisobim/sozlamalar/` | Sozlamalar |
| `/hisobim/hisobni-toldirish/` | Balansni to'ldirish |
| `/hisobim/parolni-tiklash/` | Parolni tiklash |

### 7.3. Kitoblar (`/kitoblar/`)

| Manzil | Sahifa |
|---|---|
| `/kitoblar/` | Katalog |
| `/kitoblar/<id>/` | Kitob sahifasi |
| `/kitoblar/<id>/sotib-olish/` | Xarid (to'lov formasi) |
| `/kitoblar/<id>/yoqtirish/` | Yoqtirish |
| `/kitoblar/<id>/sharh/` | Sharh qoldirish |
| `/kitoblar/sharh/<id>/javob/` | Sharhga javob |
| `/kitoblar/<id>/oqish/` | Kitobni brauzerda o'qish |
| `/kitoblar/<id>/fayl/` | PDF ni ochish (xarid tekshiriladi) |
| `/kitoblar/<id>/yuklab-olish/` | PDF ni saqlash (xarid tekshiriladi) |
| `/kitoblar/mening-kutubxonam/` | Sotib olingan kitoblar |
| `/kitoblar/kabinet/` | Sotuvchi kabineti |
| `/hisobim/pul-yechish/` | Pul yechish so'rovi |
| `/kitoblar/mening-kitoblarim/` | Sotuvchining kitoblari |
| `/kitoblar/qoshish/` | Kitob qo'shish |
| `/kitoblar/<id>/tahrirlash/` | Kitobni tahrirlash |
| `/kitoblar/mualliflar/` | Mualliflar ro'yxati |
| `/kitoblar/export/kitoblar/excel/` | Excel eksport |
| `/kitoblar/export/kitoblar/pdf/` | PDF eksport |

### 7.4. AI yordamchi

| Manzil | Vazifasi |
|---|---|
| `/ai/` | AI suhbat sahifasi |
| `/ai/yuborish/` | Xabar yuborish |
| `/ai/tozalash/` | Suhbatni tozalash |
| `/ai/tavsif/` | Kitob tavsifini generatsiya qilish |
| `/ai/rasm/` | Rasm generatsiya qilish |

### 7.5. Administrator paneli

| Manzil | Sahifa |
|---|---|
| `/boshqaruv-panel/kirish/` | Maxfiy kirish |
| `/boshqaruv-panel/statistika/` | Statistika |
| `/boshqaruv-panel/foydalanuvchilar/` | Foydalanuvchilar ro'yxati |
| `/boshqaruv-panel/foydalanuvchilar/<id>/` | Foydalanuvchi kartochkasi |
| `/boshqaruv-panel/foydalanuvchilar/<id>/bloklash/` | Bloklash |
| `/boshqaruv-panel/foydalanuvchilar/<id>/ochirish/` | O'chirish |
| `/boshqaruv-panel/foydalanuvchilar/<id>/xabar/` | Xabar yuborish |
| `/boshqaruv-panel/foydalanuvchilar/<id>/parol/` | Parolni yangilash |
| `/boshqaruv-panel/elon/` | E'lon tarqatish |
| `/boshqaruv-panel/pul-yechish/` | Pul yechish so'rovlari |
| `/django-boshqaruv-x9f2/` | Django admin |

---

## 8. REST API

Manzil: `/api/`. Autentifikatsiya: sessiya asosida. Ruxsat: o'qish hammaga
ochiq, yozish faqat autentifikatsiyadan o'tganlarga. Sahifalash: 12 yozuv.

| Endpoint | Metodlar | Izoh |
|---|---|---|
| `/api/genres/` | GET, POST | Janrlar |
| `/api/authors/` | GET, POST, PUT, DELETE | Mualliflar |
| `/api/books/` | GET, POST, PUT, DELETE | Kitoblar (filtr va qidiruv bilan) |
| `/api/reviews/` | GET, POST | Sharhlar |
| `/api/my-purchases/` | GET | Joriy foydalanuvchining xaridlari |
| `/api-auth/` | — | DRF kirish/chiqish |

---

## 9. O'rnatish va ishga tushirish

### 9.1. Talablar

- Python 3.11 yoki undan yuqori
- Git
- PostgreSQL 16 (ixtiyoriy — standart holda SQLite ishlatiladi)

### 9.2. Ishga tushirish (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env

python manage.py migrate
python manage.py seed_admin
python manage.py runserver
```

### 9.3. Ishga tushirish (Linux / macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env

python manage.py migrate
python manage.py seed_admin
python manage.py runserver
```

Loyiha manzili: http://127.0.0.1:8000/

### 9.4. PostgreSQL'ga o'tish

1. `.env` faylida `USE_SQLITE=False` qilinadi
2. `python manage.py setup_db` — baza va foydalanuvchini yaratadi
3. `python manage.py migrate`

### 9.5. Konfiguratsiya (`.env`)

| O'zgaruvchi | Vazifasi |
|---|---|
| `DEBUG` | Ishlab chiqish rejimi |
| `SECRET_KEY` | Django maxfiy kaliti |
| `ALLOWED_HOSTS` | Ruxsat etilgan hostlar |
| `USE_SQLITE` | `True` → SQLite, `False` → PostgreSQL |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL ulanishi |
| `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL` | AI sozlamalari |
| `AI_RATE_LIMIT_MESSAGES`, `AI_RATE_LIMIT_IMAGES`, `AI_RATE_LIMIT_WINDOW` | AI so'rovlari chegarasi |
| `REDIS_URL` | Redis manzili (bo'sh bo'lsa xotiradagi kesh) |
| `CACHE_TIMEOUT_HOME`, `CACHE_TIMEOUT_CATALOG` | Keshda saqlash muddati |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Pochta (parolni tiklash) |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL` | Boshlang'ich administrator |
| `ADMIN_TELEGRAM_URL` | Administrator bilan bog'lanish havolasi |

### 9.6. Diagnostika buyruqlari

```
python manage.py check_db     # baza: ulanish, jadvallar, ma'lumotlar
python manage.py check_ai     # AI: .env, kalit, provayder, sinov so'rovi
python manage.py check_cache  # kesh: Redis ulanishi, versiya, chegara
python manage.py setup_db    # PostgreSQL bazasi va foydalanuvchisini yaratish
python manage.py seed_admin  # boshlang'ich administratorni yaratish
```

---

## 10. Testlash

| Turi | Tavsifi |
|---|---|
| Birlik testlari | Modellar, formalar va yordamchi funksiyalar (`tests.py`) |
| Integratsion testlar | Ko'rinishlar (views), autentifikatsiya, rollar bo'yicha kirish nazorati |
| API testlari | DRF endpointlari |
| Qo'lda tekshirish | Uch til, ikki mavzu, barcha rollar bo'yicha to'liq stsenariy |

Avtomatik testlar asosan pullik kontent atrofidagi ruxsatlarni va pul
harakatini qamrab oladi: faylga kirish huquqi, o'qish holatini saqlash,
xarid, pul yechish so'rovi va uni ko'rib chiqish, kabinetdagi hisob-kitob.

Testlarni ishga tushirish:

```
python manage.py test
```

---

## 11. Yetkazib beriladigan natijalar

1. To'liq ishlaydigan veb-ilova manba kodi
2. Ma'lumotlar bazasi migratsiyalari
3. Uch tilli tarjima fayllari (`.po` va tayyor `.mo`)
4. `README.md` — o'rnatish va foydalanish qo'llanmasi
5. Ushbu texnik topshiriq hujjati
6. `.env.example` — konfiguratsiya namunasi
7. Diagnostika buyruqlari

---

## 12. Cheklovlar va eslatmalar

1. **To'lov tizimi haqiqiy emas.** Bu o'quv loyihasi — bank kartalari bilan
   real integratsiya (Payme, Click, Uzcard) amalga oshirilmagan. Karta
   ma'lumotlari saqlanmaydi, faqat oxirgi 4 raqam chek uchun qoladi.
2. **Parolni ko'rsatib bo'lmaydi.** Django parollarni bir tomonlama hash
   qilib saqlaydi. Uning o'rniga yangi parol belgilash imkoniyati berilgan.
3. **AI provayderining bepul limiti bor.** Kalit egasining hududi va tarifi
   bo'yicha so'rovlar soni chegaralangan bo'lishi mumkin.
4. **`.env` fayli repozitoriyaga tushmaydi.** Har bir yangi kompyuterda uni
   `.env.example` dan nusxalab, API kalitlarni qayta kiritish kerak.
5. **Maxfiy kalitlarni `.env.example` ga yozmaslik kerak** — bu fayl git'ga
   tushadi va kalit oshkor bo'ladi.

---

## 13. Kelgusi rivojlantirish imkoniyatlari

| № | Imkoniyat |
|---|---|
| 1 | Istaklar ro'yxati (wishlist) |
| 2 | Haqiqiy to'lov tizimlari integratsiyasi (Payme, Click) |
| 3 | Kitoblarni tavsiya qilish tizimi (AI asosida) |
| 4 | Mobil ilova uchun token asosidagi API autentifikatsiyasi |
| 5 | Bulutli hostingga joylashtirish |
| 6 | Email va push bildirishnomalar |

---

*Hujjat oxiri*
