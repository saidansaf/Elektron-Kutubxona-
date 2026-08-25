# Mobil ilova (PWA) — bepul, do'konsiz

Sayt telefonga **ilova qilib o'rnatiladi**: bosh ekranda o'z belgisi
paydo bo'ladi, ochilganda manzil satri ko'rinmaydi va u oddiy ilovadek
ishlaydi. Play Market ham, App Store ham kerak emas, hech qanday to'lov
yo'q.

Bu texnologiya **PWA** (Progressive Web App) deb ataladi.

---

## Foydalanuvchi nima qiladi

Tepadagi tasmada **«Yuklab olish»** tugmasi turadi.

| Brauzer | Nima bo'ladi |
|---|---|
| Chrome (Android, Windows) | Tugma bosilganda brauzerning o'z o'rnatish oynasi chiqadi |
| Edge | Xuddi shunday |
| Safari (iPhone) | Avtomatik oyna yo'q — tugma qo'lda o'rnatish yo'riqnomasini ko'rsatadi |
| Firefox | Xuddi Safari kabi |

Ilova o'rnatilgach tugma o'z-o'zidan yo'qoladi.

> **Muhim:** o'rnatish faqat **HTTPS** da ishlaydi. Render buni o'zi
> beradi. `http://127.0.0.1` da sinov qilsangiz tugma yo'riqnomani
> ko'rsatadi, o'rnatish oynasi chiqmaydi — bu xato emas.

---

## Ichkarida nima bor

Uchta qism, uchalasi ham **saytning ildizidan** beriladi:

| Manzil | Nima | Qayerda yozilgan |
|---|---|---|
| `/manifest.webmanifest` | Ilovaning nomi, rangi va belgilari | `apps/core/pwa_views.py` |
| `/sw.js` | Brauzer ichida ishlaydigan skript | `apps/core/pwa_views.py` |
| `/oflayn/` | Internet yo'qligida ko'rsatiladigan sahifa | `templates/core/offline.html` |

### Nega ildizdan, `static/` dan emas

Service worker **faqat o'zi turgan papka va undan pastdagi** manzillarni
boshqara oladi. `/static/js/sw.js` da tursa u faqat `/static/js/` ni
ko'radi — butun saytga ta'sir qila olmaydi va ilova o'rnatilmaydi.
Shuning uchun u Django orqali `/sw.js` dan beriladi.

Manifest esa foydalanuvchi tiliga tarjima qilinadi, ya'ni u ham
o'zgaruvchan — statik fayl bo'la olmaydi.

### Kesh qoidasi

Bu do'kon, shuning uchun qoida qat'iy:

* **Sahifalar (HTML) hech qachon keshlanmaydi.** Aks holda kitob narxi
  o'zgargach foydalanuvchi eski narxni ko'rib qolardi. Internet yo'q
  bo'lsagina `/oflayn/` sahifasi ko'rsatiladi.
* **CSS, JS va rasmlar keshlanadi.** Ularning nomida o'zgarish belgisi
  (hash) bor: fayl yangilansa nomi ham o'zgaradi, ya'ni eski keshni
  ishlatib qo'yish xavfi yo'q.

Natijada ilova tez ochiladi, lekin ma'lumot doim yangi bo'ladi.

---

## Belgilarni (ikonkalarni) o'zgartirish

Belgilar `static/img/` ichida:

```
icon-192.png             Android
icon-512.png             Android, o'rnatish oynasi
icon-maskable-512.png    Android belgini dumaloq kessa ham butun qoladi
apple-touch-icon.png     iPhone
```

Ular qo'lda chizilmaydi — skript yasaydi:

```bash
python scripts/make_icons.py
```

Rang yoki shaklni o'zgartirish uchun `scripts/make_icons.py` ni
tahrirlang va qayta ishga tushiring. Shakl `static/img/favicon.svg`
bilan bir xil tutilgan.

---

## Service worker'ni yangilash

`apps/core/pwa_views.py` ichidagi mantiq o'zgarsa, o'sha fayldagi
`CACHE_VERSION` ni oshiring:

```python
CACHE_VERSION = "v2"
```

Shunda brauzerdagi eski kesh tashlab yuboriladi. Worker faylining o'zi
hech qachon keshlanmaydi (`no-cache`), shuning uchun yangi versiya
foydalanuvchiga darrov yetib boradi.

---

## Tekshirish

Chrome'da: **F12 → Application**

| Bo'lim | Nimani ko'rish kerak |
|---|---|
| Manifest | Nom, ranglar va uchta belgi ko'rinadi, xato yo'q |
| Service Workers | Holati `activated and is running`, qamrovi (`Scope`) `/` |
| Cache Storage | `kutubxona-v1` ichida `/oflayn/` va statik fayllar |

Manzil satrining o'ng chetida o'rnatish belgisi paydo bo'lsa —
hammasi joyida.

Kodda esa:

```bash
python manage.py test apps.core.test_pwa
```
