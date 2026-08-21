# To'lov tizimi (Payme va Click)

Loyihada haqiqiy to'lov protokoli to'liq yozilgan. Standart holda u
**test rejimida** ishlaydi: kod haqiqiy, faqat qarshi tomon sinov.
Kalit olingan kuni bitta sozlamani almashtirish yetadi — kodga tegilmaydi.

---

## Pul modeli: xaridorda hisob yo'q

Foydalanuvchida **balans yo'q** va "Hisobni to'ldirish" degan sahifa
ham yo'q. Har bir kitob alohida, karta orqali to'lanadi:

```
Kitobni tanlash  →  Payme yoki Click  →  Karta  →  Kitob kutubxonada
```

Kitob narxi o'zgarmaydi va uni foydalanuvchi tanlay olmaydi — summa
har doim kitob narxiga teng.

**Sotuvchining hisobi bor** — bu uning daromadi. Kitob sotilganda
sotuvchining hisobiga narx qo'shiladi, u yerdan pul yechish so'rovi
beriladi (administrator tasdiqlaydi).

Qaysi kartalar: Payme va Click sahifalarida **Uzcard, Humo, Visa,
Mastercard** qabul qilinadi. Kartani qaysi biri ekanini foydalanuvchi
o'sha yerda tanlaydi — bizning saytimizga karta ma'lumotlari umuman
kelmaydi.

Xuddi shu narsa Telegram botda ham ishlaydi: kitobni bosasiz, to'lov
tizimini tanlaysiz, havolani ochib to'laysiz — kitob o'zi keladi.

---

## To'lov qanday kechadi

```
1. Foydalanuvchi kitob sahifasida "Payme" yoki "Click" ni bosadi
        ↓
2. Bizda Payment yozuvi yaratiladi (holati: Yaratildi, summa = kitob narxi)
        ↓
3. Foydalanuvchi provayder sahifasiga yo'naltiriladi
        ↓
4. U yerda kartasini kiritadi va SMS kodni tasdiqlaydi
        ↓
5. Provayder BIZNI chaqiradi: "buyurtma bormi? summasi to'g'rimi?"
        ↓
6. Pul yechilgach yana chaqiradi: "bajarildi"
        ↓
7. ANA SHUNDA kitob beriladi va pul sotuvchiga o'tadi (Payment: To'landi)
```

**Karta raqami bizga umuman kelmaydi.** U provayderning o'z sahifasida
kiritiladi. Shuning uchun bizga PCI DSS sertifikati kerak emas — bu
juda katta yengillik.

### Holatlar

| Holat | Ma'nosi |
|---|---|
| `Yaratildi` | Buyurtma bor, provayder hali tegmagan |
| `Kutilmoqda` | Provayder tranzaksiyani ochdi |
| `To'landi` | Pul o'tdi, kitob xaridorga berildi |
| `Bekor qilindi` | Bekor qilindi. To'langan bo'lsa kitob olinib, pul sotuvchidan qaytarildi |

---

## Test rejimi

`PAYMENT_MODE=test` (standart) bo'lganda foydalanuvchi Payme/Click
saytiga emas, **o'zimizdagi sinov sahifasiga** tushadi. "To'lashni
tasdiqlash" bosilganda `apps/payments/testmode.py` Payme yoki Click
aynan yuboradigan so'rovlarni yig'adi va ularni haqiqiy protokol
kodiga uzatadi.

Ya'ni `CreateTransaction` → `PerformTransaction` zanjiri, Basic auth,
MD5 imzo, summani tiyinda solishtirish — hammasi haqiqiy yo'ldan
o'tadi. Farqi bitta: so'rovni Payme emas, o'zimiz yubordik.

Shuning uchun kalit kelgan kuni "birinchi marta ishga tushirish"
muammosi bo'lmaydi.

> Test rejimida ham imzo kaliti bor: u `SECRET_KEY` dan hosil qilinadi.
> Hech qayerga yozish shart emas, lekin imzo tekshiruvi haqiqatan
> ishlaydi.

---

## Jonli rejimga o'tish

### 1. Nima kerak

Payme va Click kalitni faqat quyidagilar bo'lsa beradi:

| Talab | Izoh |
|---|---|
| Yuridik shaxs yoki **YaTT** | Jismoniy shaxsga berilmaydi |
| **STIR** (soliq raqami) | |
| **Bank hisob raqami** | Pul shu yerga tushadi |
| **Shartnoma** | Payme/Click bilan imzolanadi |
| **Onlayn kassa / fiskal chek** | O'zbekistonda onlayn savdo uchun majburiy |

Komissiya odatda aylanmadan **~1–3%**.

Ariza: https://payme.uz/business va https://click.uz/biznesga

### 2. Kabinetda ko'rsatiladigan manzillar

Payme va Click sozlamalarida "endpoint" (yoki "URL") so'raladi.
Quyidagilarni yozing (`kutubxona-xxxx.onrender.com` o'rniga o'z
domeningiz):

| Provayder | Manzil |
|---|---|
| Payme (Merchant API) | `https://kutubxona-xxxx.onrender.com/tolov/payme/` |
| Click (Prepare) | `https://kutubxona-xxxx.onrender.com/tolov/click/` |
| Click (Complete) | `https://kutubxona-xxxx.onrender.com/tolov/click/` |

Click'da ikkala bosqich uchun bitta manzil beriladi — qaysi bosqich
ekanini `action` maydoni bildiradi.

Payme kabinetida "buyurtma raqami" maydonining nomi ham so'raladi.
Standart holda `order_id` ishlatiladi; boshqa nom bergan bo'lsangiz
`PAYME_ACCOUNT_FIELD` ga o'shani yozing.

### 3. Sozlamalar

Render → **Environment** (yoki lokal `.env`):

```
PAYMENT_MODE=live

PAYME_MERCHANT_ID=...
PAYME_KEY=...

CLICK_SERVICE_ID=...
CLICK_MERCHANT_ID=...
CLICK_SECRET_KEY=...
```

Faqat bittasi bo'lsa ham bo'ladi — kaliti to'ldirilmagan tizim
saytda ko'rinmaydi.

Saqlagach Render qayta deploy qiladi. Tekshirish (administrator
sifatida kirgan holda):

```
https://kutubxona-xxxx.onrender.com/tolov/holat/
```

Javob shunday bo'lishi kerak:

```json
{"mode": "live", "providers": ["payme", "click"],
 "payme_ready": true, "click_ready": true}
```

---

## Xavfsizlik

Webhook manzillari ochiq — ularni har kim chaqira oladi. Himoya
so'rovning **ichida**:

| Provayder | Himoya |
|---|---|
| Payme | `Authorization: Basic base64("Paycom:<PAYME_KEY>")` |
| Click | Har so'rovdagi `sign_string` — maxfiy kalit bilan hisoblangan MD5 |

Ikkalasi ham `hmac.compare_digest` bilan solishtiriladi (vaqt bo'yicha
hujumdan himoya).

Busiz istalgan odam webhook'ga "to'landi" deb yozib, kitoblarni bepul
olib ketishi mumkin bo'lardi.

Yana ikkita qoida:

- **Sinov sahifasi jonli rejimda ochilmaydi.** Aks holda kitoblarni
  haqiqiy pul to'lamasdan olish mumkin bo'lardi.
- **Takroriy so'rov ikkinchi kitob bermaydi.** Provayder javobni olmasa,
  xuddi shu so'rovni qayta yuboradi — bu normal holat va kod unga tayyor
  (`services.mark_paid` idempotent).

---

## Fayllar

| Fayl | Vazifasi |
|---|---|
| `apps/payments/models.py` | `Payment` — to'lov buyurtmasi |
| `apps/payments/services.py` | Pul harakati (kitobni berish, qaytarish) |
| `apps/payments/payme.py` | Payme Merchant API (6 metod) |
| `apps/payments/click.py` | Click SHOP-API (Prepare/Complete) |
| `apps/payments/testmode.py` | Test rejimi: provayder o'rnini bosuvchi |
| `apps/payments/views.py` | Sahifalar va webhook'lar |
| `apps/payments/tests.py` | 45 test |

---

## Telegram botda

Bot ham xuddi shu tizimdan foydalanadi:

- **Kitob sotib olish:** kitobni bosasiz → bot to'lov tizimini so'raydi →
  havolani ochib to'laysiz → kitob o'zi kutubxonaga tushadi
- **🧾 To'lovlarim:** xaridorning to'lovlar tarixi
- **💰 Daromadim:** faqat sotuvchida — sotuvdan tushgan pul va uni yechish

Kitob provayder tasdiqlagach beriladi, ya'ni saytdagi bilan bir xil
yo'ldan.

Bot havolani tugma qilib beradi. Telegram tugmadagi manzil HTTPS
bo'lishini talab qiladi, shuning uchun lokal kompyuterda (http) havola
oddiy matn ko'rinishida yuboriladi — bu normal.

---

## Tez-tez uchraydigan savollar

**Test rejimida ham to'lovlar tarixi to'liq ko'rinadimi?**
Ha. `Payment` yozuvlari bir xil yaratiladi, faqat pul haqiqiy emas.

**Nega foydalanuvchi balans to'ldira olmaydi?**
Ataylab: balans bo'lsa, undagi pul uchun javobgarlik bizda bo'ladi
(qaytarish, hisobot, soliq). Har bir kitobni alohida to'lash ancha
sodda va xavfsiz.

**Jonli rejimga o'tsam eski test to'lovlari nima bo'ladi?**
Bazada qoladi. Xohlasangiz administrator panelidan o'chirasiz.

**Payme "Wrong amount" deb rad etyapti.**
Summa **tiyinda** yuboriladi: 50 000 so'm = 5 000 000 tiyin. Kabinetdagi
summa formatini tekshiring.

**Click "SIGN CHECK FAILED" deyapti.**
`CLICK_SECRET_KEY` noto'g'ri yoki ortiqcha bo'shliq bilan yozilgan.
Kabinetdagi qiymat bilan belgima-belgi solishtiring.

**Kitob berilmadi, lekin pul yechildi.**
`/tolov/holat/` dan rejimni tekshiring, so'ng Render → Logs da
`payme` yoki `click` so'zi bo'yicha qidiring — xato o'sha yerda
yozilgan bo'ladi.
