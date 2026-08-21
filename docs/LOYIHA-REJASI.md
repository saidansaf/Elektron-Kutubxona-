# ELEKTRON KUTUBXONA

## Loyiha rejasi

---

| | |
|---|---|
| **Loyiha nomi** | Elektron Kutubxona |
| **Turi** | Elektron kitoblar oldi-sotdi platformasi (marketplace) |
| **Ishlab chiquvchi** | Saidansaf |
| **Repozitoriya** | https://github.com/saidansaf/Elektron-kitoblar |
| **Hujjat turi** | Loyiha rejasi (bosqichlar va vazifalar) |
| **Holati** | 7 bosqich bajarilgan, 4 bosqich qoldi |
| **Sana** | 2026-yil avgust |

---

# 1. Reja nima uchun kerak

Loyiha 2026-yil 28-iyulda boshlangan va bir necha hafta ichida katta
hajmga yetgan: 8 150 qator Python kodi, 3 070 qator CSS, 38 ta shablon,
19 ta model, 106 ta test. Bunday hajmda "keyingi nima?" degan savolga
xotiradan javob berib bo'lmaydi.

Bu hujjat uch narsani aniq qilib qo'yadi:

1. **Nima bajarilgan** — takrorlab yoki qaytadan yozib yurmaslik uchun.
2. **Nima qolgan** — qaysi tartibda va nima uchun aynan shu tartibda.
3. **Bosqich qachon tugagan hisoblanadi** — "deyarli tayyor" degan
   noaniq holat bo'lmasligi uchun. Har bir bosqichda tekshiriladigan
   mezon bor.

---

# 2. Loyihaning maqsadi

Sayt **elektron kitoblarni sotish va sotib olish** uchun mo'ljallangan.
Sotuvchi PDF kitobini narx qo'yib joylaydi, xaridor uni balansidan sotib
oladi va brauzerning o'zida o'qiydi. Pul sotuvchining balansiga tushadi,
u istagan vaqtda kartasiga yechib oladi.

Uchta rol bor: **administrator**, **sotuvchi**, **xaridor**. Interfeys
uch tilda (o'zbek, rus, ingliz), ikki temada (yorug', qorong'i) ishlaydi.
Saytga qo'shimcha sifatida Telegram bot ulanadi, lekin **sayt asosiy**
bo'lib qoladi.

---

# 3. Ish uslubi

Loyiha boshidan beri bitta qoidaga amal qilib kelinmoqda va u keyin ham
saqlanadi:

**Har bir bosqich to'liq yopiladi.** Ya'ni funksiya yozildi → uch tilga
tarjima qilindi → test yozildi → brauzerda ikkala temada ko'zdan
kechirildi → hujjatga tushdi → commit qilindi. Yarim tayyor holatda
keyingi bosqichga o'tilmaydi, chunki yig'ilib qolgan yarim ishlar keyin
bir-birini buzadi.

**Har bir muammo avval isbotlanadi, keyin tuzatiladi.** Masalan, pullik
PDF fayllar hammaga ochiqligi shunchaki taxmin qilinmadi — `curl` bilan
anonim so'rov yuborilib, HTTP 200 qaytgani ko'rsatildi. Shundan keyingina
himoya yozildi va aynan shu holatga test qo'shildi.

---

# 4. Bajarilgan bosqichlar

## 1-bosqich. Poydevor

**Nima qilindi:** Django loyihasi tuzildi, uchta ilova ajratildi
(`accounts`, `books`, `core`), sozlamalar `.env` fayldan o'qiydigan
qilindi, PostgreSQL ulandi va SQLite'ga qaytish yo'li qoldirildi
(`USE_SQLITE=1`).

**Asosiy modellar:** `User` (o'z modeli, rol va balans bilan), `Author`,
`Genre`, `Book`, `Purchase`, `Review`.

**Nega SQLite varianti kerak bo'ldi:** loyihani boshqa kompyuterda ochish
kerak bo'lganda PostgreSQL o'rnatish uzoq vaqt olardi. SQLite bilan
`python manage.py runserver` darrov ishlaydi.

## 2-bosqich. Rollar va asosiy oqimlar

Ro'yxatdan o'tish, kirish, rol tanlash, sozlamalar sahifasi. Sotuvchi
uchun kitob qo'shish/tahrirlash/o'chirish. Xaridor uchun katalog, filtr,
sotib olish, baholash va izoh yozish. Izohlarga javob berish, yoqtirish.

Maxfiy administrator kirishi (`#admin`), foydalanuvchilarni bloklash,
o'chirish, ularga xabar yozish va umumiy e'lon tarqatish.

## 3-bosqich. Ko'p tillilik va dizayn

Django `gettext` orqali uch til: `.po` fayllar to'ldirildi va
`.mo` ga kompilyatsiya qilindi. Yorug'/qorong'i tema sessiyada va
foydalanuvchi profilida saqlanadi.

**Bu bosqichda bir necha marta tuzoqqa tushildi.** `makemessages` yangi
qatorlarga o'xshash eski qatorlardan taxmin qo'yib, ularni `fuzzy` deb
belgilaydi. Bir marta 42 ta, keyin 57 ta noto'g'ri tarjima paydo bo'lgan
("Rad etish" → "Регистрация"). Endi har `makemessages` dan keyin
fuzzy'lar majburiy tekshiriladi va qo'lda tuzatiladi.

## 4-bosqich. Pullik kontentni himoyalash

**Bu eng muhim tuzatish bo'ldi.** Kitob PDF fayllari `media/` papkasida
turardi va manzilini bilgan har kim ularni **pul to'lamasdan** yuklab
olishi mumkin edi.

Yechim: fayllar `MEDIA_ROOT` dan tashqaridagi `private_media/` ga
ko'chirildi, ularga faqat ruxsat tekshirilgandan keyin `FileResponse`
orqali kirish mumkin. Ruxsati yo'q odamga 403 emas, **404** qaytariladi —
403 "fayl bor, lekin sizga ruxsat yo'q" degani, bu ham ortiqcha ma'lumot.

## 5-bosqich. O'qish va sotuvchi kabineti

**Brauzerda o'qish:** PDF.js kutubxonasi loyihaning o'ziga joylandi
(tashqi CDN'ga bog'liq bo'lmaslik uchun). Sahifalar ko'rinish maydoniga
kirganda yuklanadi, o'qilgan joy serverga saqlanadi — telefonda
boshlangan kitobni kompyuterda davom ettirish mumkin.

**Sotuvchi kabineti:** umumiy daromad, sotilgan nusxalar, xaridorlar
soni, 30 kunlik diagramma va har bir kitob kesimidagi jadval.

**Bu yerda jiddiy hisob xatosi topildi.** Daromad 9 barobar ko'p
ko'rsatilardi: bitta `annotate()` ichida `Sum(xaridlar)` va
`Count(sharhlar)` birga yozilgani uchun SQL ikkita jadvalni ko'paytirib
yuborgan edi. `Subquery` bilan tuzatildi va aynan shu holatga test
yozildi.

**Pul yechish:** so'rov yuborilganda summa balansdan darhol ushlab
qolinadi (aks holda bitta pulni bir necha marta so'rash mumkin bo'lardi),
administrator rad etsa qaytariladi.

## 6-bosqich. Kesh va chegaralar

Redis **ixtiyoriy** qilib ulandi: `REDIS_URL` bo'lsa ishlatiladi,
bo'lmasa xotiradagi kesh ishlatiladi.

**README'da "Redis o'chsa ham sayt ishlayveradi" deb yozilgan edi —
tekshirib ko'rilganda bu yolg'on chiqdi**, sayt 500 xato berardi.
Shundan keyin `ResilientRedisCache` yozildi: u Redis xatolarini yutib
yuboradi va `None` qaytaradi, sayt esa kesh yo'qdek ishlayveradi. Redis
o'chirilgan holatga alohida test bor.

Natija: bosh sahifa 18 ta so'rov / 364 ms dan 0 ta so'rov / 4 ms ga
tushdi. AI so'rovlariga soatlik chegara qo'yildi.

## 7-bosqich. Telegram bot va zamonaviy dizayn

**Bot:** hisobni 6 xonali bir martalik kod bilan ulash, katalog, qidiruv,
balansdan sotib olish, PDF olish, istaklar va bildirishnomalar. Bot
saytning **o'sha bazasi** bilan ishlaydi, o'z bazasi yo'q.

**Xarid mantiqi bitta joyga chiqarildi** (`apps/books/services.py`) —
sayt ham, bot ham shu funksiyani chaqiradi. Ikki nusxada yozilsa, biri
o'zgarganda ikkinchisi eskirib, pul hisobida farq paydo bo'lardi.

**Botning ishga tushmasligiga sabab bo'lgan uchta xato tuzatildi:**
`ENABLE_MIDDLEWARE` bayrog'i, qolib ketgan webhook (long polling bilan
birga ishlamaydi va bot hech qanday xabarni ko'rmaydi), va kutubxona
o'rnatilmaganda chiqadigan tushunarsiz xato.

**Dizayn** ko'k-moviy palitraga o'tkazildi, header suzib turgan shisha
panelga aylandi, kitob kartochkasi butunlay bosiladigan bo'ldi.

**Kirish oqimi soddalashtirildi:** katalog va kitob ma'lumotlari
hammaga ochiq, ro'yxatdan o'tish faqat **sotib olishda** so'raladi va
undan keyin foydalanuvchi o'sha kitobga qaytariladi.

---

# 5. Hozirgi holat raqamlarda

| Ko'rsatkich | Qiymat |
|---|---|
| Python kodi | 8 150 qator |
| CSS | 3 070 qator |
| HTML shablonlar | 38 ta |
| Ma'lumotlar bazasi modellari | 19 ta |
| Testlar | 106 ta, hammasi o'tadi |
| Tillar | 3 ta (uz / ru / en), bo'sh tarjima yo'q |
| Tashxis buyruqlari | 4 ta (`check_db`, `check_ai`, `check_cache`, `check_bot`) |
| Commitlar | 23 ta |

---

# 6. Qolgan bosqichlar

Quyidagi tartib tasodifiy emas. **8-bosqich birinchi turibdi, chunki
undan keyingi hamma narsa unga bog'liq:** sayt internetda turmaguncha
Telegram botdagi havolalar boshqa qurilmada ochilmaydi, haqiqiy to'lovni
ulab bo'lmaydi va foydalanuvchi sinovini o'tkazib bo'lmaydi.

## 8-bosqich. Serverga chiqarish (deploy)

**Nima uchun birinchi:** hozir sayt faqat ishlab chiquvchining
kompyuterida ishlaydi (`127.0.0.1`). Telegram botdagi "Saytda ochish"
havolasi boshqa odamda ochilmaydi. Loyiha real foydalanuvchiga
ko'rinmaguncha keyingi ishlarning ma'nosi kam.

**Vazifalar:**

1. Server tanlash va olish (VPS yoki PaaS)
2. PostgreSQL va Redis'ni serverda o'rnatish
3. Gunicorn + Nginx sozlash, statik fayllarni Nginx orqali berish
4. Domen ulash va HTTPS sertifikati (Let's Encrypt)
5. `DEBUG=False`, `ALLOWED_HOSTS`, `SECURE_*` sozlamalarini yoqish
6. **`.env` dagi barcha parollarni yangilash** — hozir `ADMIN_PASSWORD`
   `settings.py` da standart qiymat sifatida turibdi, ya'ni kodni ko'rgan
   har kim uni biladi
7. `private_media/` papkasini Nginx orqali **berilmaydigan** qilib
   qo'yish (u faqat Django orqali chiqishi kerak)
8. Botni `systemd` xizmati sifatida ishga tushirish (qulab tushsa
   avtomatik qayta ishga tushsin)
9. Bazani kunlik zaxiralash

**Bosqich tugadi deb hisoblanadi:** sayt domen orqali HTTPS'da ochiladi,
bot boshqa telefondan ishlaydi, server qayta yuklangandan keyin hammasi
o'zi ko'tariladi, va zaxiradan tiklash bir marta sinab ko'rilgan.

**Taxminiy vaqt:** 2–3 kun.

## 9-bosqich. Avtomatik tekshiruv (CI)

**Nima uchun kerak:** hozir testlar qo'lda ishga tushiriladi. Deploydan
keyin buzilgan kodning serverga chiqib ketishi mumkin.

**Vazifalar:**

1. GitHub Actions: har `push` da `python manage.py test` ishlasin
2. `ruff` yoki `flake8` bilan kod uslubini tekshirish
3. Tarjimalarda bo'sh yoki `fuzzy` qator qolmaganini tekshiruvchi qadam
   (bu loyihada bir necha marta muammo bo'lgan)
4. Testlar yashil bo'lmasa `main` ga qo'shishni taqiqlash

**Bosqich tugadi:** testi buzilgan o'zgarish `main` ga tusha olmaydi.

**Taxminiy vaqt:** 1 kun.

## 10-bosqich. Haqiqiy to'lov ✅ (kod tayyor, kalit kutilmoqda)

**Bajarildi:** Payme Merchant API va Click SHOP-API to'liq yozildi.
Xaridordagi hisob (balans) butunlay olib tashlandi — endi har bir kitob
alohida, karta orqali to'lanadi. Karta ma'lumotlari saytga umuman
kelmaydi va kitob faqat provayder tasdiqlagach beriladi.

| Vazifa | Holati |
|---|---|
| Payme Merchant API (6 metod) | ✅ |
| Click SHOP-API (Prepare / Complete) | ✅ |
| Imzo va parol tekshiruvi (`compare_digest`) | ✅ |
| Takroriy so'rovdan himoya (idempotentlik) | ✅ |
| To'langandan keyin bekor qilish → pulni qaytarish | ✅ |
| Botda ham xuddi shu oqim | ✅ |
| Xaridorda balans yo'q, faqat karta | ✅ |
| Test rejimi (kalitsiz to'liq sinash) | ✅ |
| 45 ta test | ✅ |
| Haqiqiy karta bilan to'lov | ⏳ kalit kutilmoqda |

**Nega hali "jonli" emas:** Payme va Click kalitni faqat YaTT/yuridik
shaxsga, shartnoma va bank hisobidan keyin beradi. Shu sababli loyiha
`PAYMENT_MODE=test` da turibdi: protokol haqiqiy yo'ldan o'tadi, pul
esa yechilmaydi.

**Kalit kelganda:** Render → Environment da `PAYMENT_MODE=live` va
kalitlar qo'yiladi. **Kodga tegilmaydi.** Batafsil: `docs/TOLOV.md`.

## 11-bosqich. Foydalanish qulayligi va yakuniy sayqal

**Vazifalar:**

1. **Ob-havo sahifasidagi muammoni tuzatish** — geolokatsiya so'roviga
   javob berilmasa sahifa kutib qotib qoladi. Vaqt chegarasi (timeout)
   va "shahar nomini yozing" varianti qo'shilishi kerak
2. Telefon ekranida to'liq tekshiruv (menyu, kitob o'quvchi, jadvallar)
3. Kirish qulayligi: klaviatura bilan yurish, ekran o'quvchi uchun
   `aria` atributlari, rang kontrasti
4. Xato sahifalari (404, 500) loyiha dizaynida
5. `sitemap.xml`, `robots.txt`, kitob sahifalari uchun meta teglar
6. Sahifalarni ochilish tezligini o'lchash va rasmlarni siqish

**Bosqich tugadi:** telefonda hamma asosiy oqim ishlaydi, ob-havo
sahifasi qotib qolmaydi, xato sahifalari o'z ko'rinishida.

**Taxminiy vaqt:** 2–3 kun.

---

# 7. Keyinroq ko'rib chiqiladigan g'oyalar

Bular rejaga kiritilmagan — avval yuqoridagi 4 bosqich tugashi kerak.
Lekin foydalanuvchi soni oshsa, ular kerak bo'lishi mumkin:

| G'oya | Nima beradi |
|---|---|
| Audiokitoblar | PDF'dan tashqari mp3 sotish |
| Obuna (podpiska) | Oylik to'lov bilan cheksiz o'qish |
| Chegirma va promokod | Sotuvni rag'batlantirish |
| Tavsiya tizimi | "Bu kitobni olganlar buni ham olishgan" |
| Sotuvchi sahifasi | Har bir sotuvchining o'z do'koni |
| PWA | Telefonga ilova sifatida o'rnatish, oflayn o'qish |
| Elektron kvitansiya | Xariddan keyin PDF chek yuborish |

---

# 8. Ma'lum kamchiliklar

Bu ro'yxat ochiq saqlanadi — yashirilgan kamchilik topilmagan kamchilik
emas, keyinroq qimmatroq tushadigan kamchilik.

| Kamchilik | Xavfi | Qachon tuzatiladi |
|---|---|---|
| `ADMIN_PASSWORD` `settings.py` da standart qiymat sifatida turibdi | **Yuqori** — kodni ko'rgan har kim admin parolini biladi | 8-bosqich |
| Deploy va CI yo'q | O'rta — buzilgan kod sezilmay qolishi mumkin | 8–9-bosqich |
| To'lov kodi tayyor, lekin `test` rejimida | O'rta — jonli rejim uchun YaTT va shartnoma kerak | 10-bosqich (kod bajarildi) |
| Ob-havo sahifasi geolokatsiyasiz qotib qoladi | Past — alohida sahifa, asosiy oqimga tegmaydi | 11-bosqich |
| Kitob muqovasi ixtiyoriy, ko'p kitob muqovasiz | Past — ko'rinish masalasi | 11-bosqich |

---

# 9. Xavflar

| Xavf | Ehtimoli | Nima qilinadi |
|---|---|---|
| To'lov tizimi hujjatlari chalkash bo'lib, 10-bosqich cho'zilishi | O'rta | Avval sinov (test) muhitida ishlab ko'riladi, real pulga keyin o'tiladi |
| Serverda PostgreSQL sozlash muammo berishi | Past | `check_db` buyrug'i muammoni o'zi topib aytadi |
| Foydalanuvchi soni oshib, server yetmay qolishi | Past | Kesh allaqachon tayyor; kerak bo'lsa server kuchaytiriladi |
| Telegram API bloklanishi | O'rta | Bot ixtiyoriy — bloklansa sayt to'liq ishlayveradi |
| Bitta odam ishlayotgani (avtobus omili) | Yuqori | Kod izohlangan, 4 ta hujjat yozilgan, 106 ta test yo'l ko'rsatadi |

---

# 10. Umumiy jadval

| Bosqich | Holati | Vaqt |
|---|---|---|
| 1. Poydevor | ✅ Bajarildi | — |
| 2. Rollar va asosiy oqimlar | ✅ Bajarildi | — |
| 3. Ko'p tillilik va dizayn | ✅ Bajarildi | — |
| 4. Pullik kontentni himoyalash | ✅ Bajarildi | — |
| 5. O'qish va sotuvchi kabineti | ✅ Bajarildi | — |
| 6. Kesh va chegaralar | ✅ Bajarildi | — |
| 7. Telegram bot va dizayn | ✅ Bajarildi | — |
| 8. Serverga chiqarish | ⬜ Keyingi | 2–3 kun |
| 9. Avtomatik tekshiruv (CI) | ⬜ Rejada | 1 kun |
| 10. Haqiqiy to'lov | ⬜ Rejada | 3–5 kun |
| 11. Qulaylik va sayqal | ⬜ Rejada | 2–3 kun |

**Qolgan ish:** taxminan **8–12 ish kuni**.

---

# 11. Keyingi qadam

Eng yaqin vazifa — **8-bosqich, serverga chiqarish**. Undan boshlash
kerak, chunki qolgan uchta bosqich ham unga bog'liq: CI deploy'ga
o'zgarishlarni yetkazadi, to'lov tizimi webhook uchun ochiq HTTPS manzil
talab qiladi, qulaylik sinovi esa haqiqiy qurilmalarda o'tkaziladi.

Boshlash uchun kerak bo'ladigan yagona qaror — **server qayerdan
olinishi**. Qolganini shu hujjatdagi ro'yxat bo'yicha ketma-ket bajarish
mumkin.
