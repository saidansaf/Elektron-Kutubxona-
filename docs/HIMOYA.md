# Loyihani himoya qilish

Ustozga loyihani ko'rsatish va tushuntirish uchun qo'llanma: 10 daqiqalik
demo ssenariysi, texnik asoslar va beriladigan savollarga javoblar.

| | |
|---|---|
| Python kodi | 11 615 qator |
| Testlar | 226 ta |
| Modellar | 19 ta |
| Tillar | 3 ta (uz / ru / en) |
| Shablonlar | 40 ta |
| Commitlar | 39 ta |

---

## 1. Bir jumlada nima deyish

Birinchi 30 soniya — ustoz loyihaning nima ekanini shu yerda tushunadi.

> "Bu — elektron kitoblar bozori. Sotuvchi PDF kitobini narx qo'yib
> joylaydi, xaridor uni Payme yoki Click orqali kartadan to'lab sotib
> oladi va brauzerning o'zida o'qiydi. Sayt uch tilda ishlaydi, Telegram
> boti bor va u sayt bilan **bitta bazada** ishlaydi."

Keyin darrov saytni oching. Uzoq gapirmang — ko'rsating.

---

## 2. 10 daqiqalik demo

Aynan shu tartibda.

### 0:00 — Bosh sahifa

Yangi kitoblar, eng yuqori baholangan, statistika. Til tanlagichni bosib
**ruschaga**, keyin tema tugmasini bosib **qorong'iga** o'ting.

> Interfeys uch tilda va ikki temada. Bu shunchaki matn almashtirish emas —
> Django'ning gettext tizimi, 678 ta tarjima qatori.

### 1:30 — Katalog va filtr

Til, janr, muallif, narx bo'yicha filtr. Saralashni almashtiring.

> Katalog keshlanadi. Yangi kitob qo'shilsa kesh o'zi yangilanadi —
> versiya raqami orqali, muddat tugashini kutmaydi.

### 3:00 — Kitobni sotib olish

Kitobni oching → **Sotib olish** → Payme yoki Click → sinov sahifasida
**To'lashni tasdiqlash**.

> Karta ma'lumotlari bizning saytimizga umuman kelmaydi — ular Payme
> sahifasida kiritiladi. Shuning uchun bizga PCI DSS sertifikati kerak
> emas. Hozir test rejimida: protokol haqiqiy, faqat pul yechilmaydi.

### 4:30 — Brauzerda o'qish

Mening kutubxonam → kitobni oching. Varaqlang, masshtabni o'zgartiring,
sahifani yodda saqlashini ko'rsating.

> PDF.js kutubxonasi loyihaning ichida — tashqi CDN'ga bog'liq emas.
> To'xtagan sahifa serverga saqlanadi, boshqa qurilmadan davom ettirsa
> bo'ladi.

### 5:30 — Sotuvchi kabineti

Sotuvchi hisobiga kiring: daromad, 30 kunlik grafik, kitoblar kesimidagi
jadval, Excel eksport.

> Bu yerda jiddiy hisob xatosi bo'lgan — daromad 9 barobar ko'p
> ko'rsatilardi. Sababi: bitta `annotate()` ichida ikkita jadval bo'yicha
> `Sum` va `Count` yozilgani. `Subquery` bilan tuzatildi va shu holatga
> alohida test yozildi.

### 7:00 — Telegram bot

Telefonda botni oching: katalog, kitob qo'shish, sotib olish. Botda
qo'shilgan kitobni saytda yangilab ko'rsating.

> Bot alohida dastur emas va o'z bazasi yo'q. Xarid mantiqi bitta faylda —
> sayt ham, bot ham shu funksiyani chaqiradi. Ikki nusxada yozilsa, biri
> o'zgarganda pul hisobida farq paydo bo'lardi.

### 8:30 — Administrator paneli

Manzil oxiriga `#admin` qo'shing. Statistika, foydalanuvchilar, bloklash,
e'lon tarqatish, pul yechish so'rovlari.

> Admin kirish sahifasining manzili taxmin qilib bo'lmaydigan qilib
> qo'yilgan va u hech qayerda havola sifatida chiqmaydi.

### 9:30 — Qo'shimchalar

AI yordamchi (kitob haqida savol bering) va ob-havo sahifasi
(davlat → shahar tanlash).

---

## 3. Texnik qismi

### Texnologiyalar

Django 5.2, Django REST Framework, PostgreSQL. Frontend alohida
framework'siz — Django shablonlari va toza CSS (3 228 qator). Bu ataylab:
loyihaning og'irligi serverda, ortiqcha qatlam kerak emas edi.

### To'rtta ilova

| Ilova | Nima uchun javob beradi |
|---|---|
| `accounts` | Foydalanuvchi, rollar, pul yechish, Telegram ulanishi |
| `books` | Kitob, muallif, janr, xarid, sharh, xabarlashuv |
| `core` | Bot, AI, kesh, ob-havo, admin boshqaruvi |
| `payments` | Payme va Click protokollari |

Har biri o'z modeli, o'z testi va o'z mas'uliyat doirasi bilan.
Jami 19 ta model.

### Nega `services.py` qatlami bor

Pul harakati view'larda emas, alohida fayllarda. Sabab oddiy: xarid
saytdan ham, botdan ham, to'lov webhook'idan ham chaqiriladi. Uch joyda
uch nusxa yozilsa, biri o'zgarganda ikkinchisi eskirib qolardi va pul
hisobida farq chiqardi.

### Uchta rol

Administrator, sotuvchi, xaridor. Rol `User` modelining maydoni, ruxsatlar
esa dekoratorlar orqali (`@seller_required`, `@buyer_required`).

---

## 4. Eng kuchli beshta nuqta

Bular loyihani kursdosh ishlaridan ajratib turadi. Kamida ikkitasini
ayting.

### 1. Pullik fayllar himoyasi — isbot bilan

Kitob PDF'lari `media/` da turardi va manzilini bilgan har kim ularni
**pul to'lamasdan** yuklab olardi. Buni taxmin qilmadim — `curl` bilan
anonim so'rov yuborib, HTTP 200 qaytganini ko'rsatdim.

Yechim: fayllar `MEDIA_ROOT` dan tashqariga ko'chirildi. Ruxsati yo'q
odamga **403 emas, 404** qaytariladi — 403 "fayl bor, lekin sizga ruxsat
yo'q" degani, bu ham ortiqcha ma'lumot.

### 2. To'lovda idempotentlik

Payme va Click javobni olmasa, xuddi shu so'rovni qayta yuboradi. Kod
bunga tayyor bo'lmasa, bitta to'lovdan foydalanuvchi ikkita kitob olib
qo'yardi.

Takroriy so'rov ikkinchi kitob bermaydi va javob ham bir xil qaytadi —
aks holda Payme uni xato deb hisoblaydi.

### 3. Redis o'chsa ham sayt ishlaydi

README'da "Redis o'chsa ham ishlayveradi" deb yozgan edim. Tekshirib
ko'rganimda bu **yolg'on chiqdi** — sayt 500 xato berardi.

Shundan keyin `ResilientRedisCache` yozildi: u ulanish xatosini yutadi va
"keshda topilmadi" deb ko'rsatadi, sahifa esa oddiy holicha bazadan
hisoblanadi. Redis o'chirilgan holatga alohida test bor.

### 4. Bot va sayt — bitta manba

Botda kitob qo'shilsa saytda darrov ko'rinadi va aksincha. Orada hech
qanday sinxronizatsiya yo'q, chunki baza bitta. Buni testlar ham
tekshiradi: bot orqali amal bajariladi, keyin saytdagi so'rovda natija
bor-yo'qligi tekshiriladi.

### 5. 226 ta test

Testlar "ishladi" degan holatni emas, ko'proq **buzilgan** holatlarni
tekshiradi: noto'g'ri imzo, mos kelmagan summa, takroriy so'rov, begona
buyurtma, ruxsatsiz fayl so'rovi.

---

## 5. Beriladigan savollar

**To'lov haqiqiymi?**

Protokol haqiqiy — Payme Merchant API ning oltita metodi ham, Click ning
Prepare/Complete bosqichlari ham to'liq yozilgan va imzo tekshiruvi
ishlaydi. Hozir **test rejimida**, chunki haqiqiy kalit uchun YaTT,
shartnoma va bank hisobi kerak. Sinov sahifasi Payme aynan yuboradigan
so'rovlarni yig'ib, ularni haqiqiy protokol kodiga uzatadi. Kalit kelgan
kuni Environment'da bitta qatorni almashtiraman — kodga tegilmaydi.

**Nega Django, React emas?**

Loyihaning og'irligi serverda: ruxsatlar, pul hisobi, to'lov protokollari,
fayl himoyasi. Bu ishlarni frontend qila olmaydi. React qo'shilsa ikkinchi
loyiha paydo bo'lardi — alohida qurish, alohida joylashtirish, API va
sahifa o'rtasida takrorlanuvchi mantiq. Interaktiv joylar (PDF o'quvchi,
ob-havo) toza JavaScript bilan yozilgan.

**Xavfsizlikka nima qildingiz?**

- Pullik PDF'lar ochiq papkada emas, ruxsat tekshirilgandan keyin beriladi
- Webhook'larda Payme uchun parol, Click uchun MD5 imzo — ikkalasi ham
  `compare_digest` bilan solishtiriladi
- Parollar Django'ning standart hashlash tizimida, hech qayerda ochiq emas
- Maxfiy kalitlar `.env` da, u Git'ga hech qachon tushmaydi
- Admin kirish manzili taxmin qilib bo'lmaydigan
- Serverda HTTPS majburiy, HSTS va xavfsiz cookie'lar yoqilgan

**Testlar nimani tekshiradi?**

Eng ko'p e'tibor pul va ruxsatga: ruxsatsiz odam faylni ololmasligi,
takroriy to'lov ikkinchi kitob bermasligi, pul yechish so'rovi summani
to'g'ri ushlab qolishi, rad etilganda qaytarishi. Har topilgan xatoga test
yoziladi — shu xato qaytadan chiqsa test darrov aytadi.

**Sayt qayerda turibdi?**

Render.com bepul tarifida. Sayt va Telegram bot **bitta xizmatda**
ishlaydi: bepul tarifda ikkinchi doimiy jarayon berilmaydi, shuning uchun
bot long polling emas, **webhook** orqali ishlaydi — Telegram yangilikni
saytning o'ziga yuboradi.

**Sayt nega sekin ochiladi?**

Bepul tarifda xizmat 15 daqiqa jimlikdan keyin uxlaydi va uyg'onishi
~50 soniya oladi. Bu loyihaning kamchiligi emas, tarif xususiyati. Kod
tomonda tezlik uchun: javoblar siqiladi (gzip), so'rovlar kutayotganda
bir-birini to'smaydi, bosh sahifa va katalog keshlanadi, ro'yxatlarda
N+1 so'rov yo'q.

**O'zingiz yozdingizmi?**

Rostini ayting. Yaxshi javob: qaysi qismni qanday qurganingizni va **nega
aynan shunday** qilganingizni tushuntirish. Masalan: nega xarid mantiqi
alohida faylda, nega 403 emas 404 qaytariladi, nega takroriy so'rov
ikkinchi kitob bermasligi kerak.

**Yana nima qo'shish mumkin?**

Rejadagi qolgan ishlar: GitHub Actions orqali avtomatik test (har
push'da), haqiqiy to'lov kaliti, mobil ekranda yakuniy sayqal. Kelajakda:
audiokitoblar, obuna modeli, kitob tavsiyalari.

---

## 6. Kamchiliklarni qanday aytish

Ustozlar yashirilgan kamchilikni topadi. Ochiq aytilgani ancha kuchli
taassurot qoldiradi.

**Aytish kerak:**

- "To'lov test rejimida, chunki kalit uchun YaTT va shartnoma kerak. Kod
  tayyor, kalit kelsa bitta sozlama almashadi."
- "Bepul tarifda yuklangan fayllar har deploydan keyin o'chadi. Doimiy
  disk pullik."
- "Bepul baza 30 kundan keyin muddati tugaydi."

**Aytmang:**

- "Hammasi tayyor, hech qanday muammo yo'q" — bu ishonchsizlik uyg'otadi
- Bilmagan narsangizni taxmin qilib aytish. To'g'ri javob: "Buni aniq
  bilmayman, tekshirib aytaman."

---

## 7. Himoyadan oldin

Bir kun oldin bajaring.

- [ ] Saytni bir marta oching (uxlab qolgan bo'lsa uyg'onib ulguradi)
- [ ] Ikkita hisob tayyorlang: bitta sotuvchi, bitta xaridor — parollarini
      yozib qo'ying
- [ ] Sotuvchida kamida 3 ta kitob, xaridorda 1 ta sotib olingan kitob
      bo'lsin
- [ ] Telefondagi Telegram botni tekshiring, hisobga ulangan bo'lsin
- [ ] Admin parolini tekshiring
- [ ] Demo ssenariysini bir marta boshdan-oyoq o'zingiz o'ynab chiqing
- [ ] Internet yo'q bo'lsa: kompyuterda `python manage.py runserver` bilan
      ko'rsatish uchun tayyor turing

---

## Yakunda nima deyish

> "Loyihada men uchun eng qiziq qismi — xatolarni topish bo'ldi. Pullik
> fayllar ochiq turgani, daromad 9 barobar ko'p hisoblangani, Redis
> o'chganda saytning yiqilgani — bularning hammasini tekshirib topdim va
> har biriga test yozdim. Shuning uchun loyihada 226 ta test bor."

---

## Qaysi hujjatni ko'rsatish

Ustoz yozma hujjat so'rasa:

| Fayl | Mazmuni |
|---|---|
| `docs/LOYIHA-HAQIDA.md` | Loyiha nima qilishi, texnologiyalar, barcha imkoniyatlar |
| `docs/TEXNIK-TOPSHIRIQ.md` | Rasmiy texnik topshiriq (raqamlangan talablar) |
| `docs/LOYIHA-REJASI.md` | Bosqichlar, bajarilgani va qolgani |
| `docs/TOLOV.md` | To'lov tizimi qanday ishlashi |
| `docs/RENDER.md` | Serverga joylashtirish |
