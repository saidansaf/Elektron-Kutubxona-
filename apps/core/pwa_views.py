"""Saytni telefonga ilova qilib o'rnatish (PWA).

Nima bu: brauzer saytni telefon ekraniga yorliq qilib qo'yadi va u
oddiy ilovadek — o'z belgisi bilan, manzil satrisiz — ochiladi.
Play Market ham, App Store ham kerak emas, pul ham to'lanmaydi.

Buning uchun uchta narsa shart:

1. **manifest** — ilovaning nomi, rangi va belgilari yozilgan fayl;
2. **service worker** — brauzer ichida ishlaydigan kichik skript;
3. **HTTPS** — Render buni o'zi beradi.

Nega bu fayllar statik emas, Django orqali beriladi:

* service worker faqat o'zi turgan papka va undan pastdagi manzillarni
  boshqara oladi. `/static/js/sw.js` da tursa, u faqat `/static/js/`
  ni ko'radi va butun saytga ta'sir qila olmaydi. Shuning uchun u
  saytning ILDIZIDAN — `/sw.js` dan beriladi.
* manifest ichidagi nom va tavsif foydalanuvchi tiliga tarjima
  qilinadi, ya'ni u har til uchun har xil bo'ladi.
"""

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_control

#: Service worker mantig'i o'zgarsa shu raqamni oshiring — brauzerdagi
#: eski kesh shunda tashlab yuboriladi.
CACHE_VERSION = "v1"


@cache_control(max_age=3600)
def manifest_view(request):
    """Ilova haqidagi ma'lumot (nom, rang, belgilar)."""
    return JsonResponse(
        {
            "name": _("Elektron Kutubxona"),
            "short_name": _("Kutubxona"),
            "description": _("O'zbek, rus va ingliz tillaridagi elektron kitoblar bozori."),
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "background_color": "#f5f9fc",
            "theme_color": "#0b5e9e",
            "lang": request.LANGUAGE_CODE,
            "dir": "ltr",
            "icons": [
                {"src": static("img/icon-192.png"), "sizes": "192x192", "type": "image/png"},
                {"src": static("img/icon-512.png"), "sizes": "512x512", "type": "image/png"},
                {
                    "src": static("img/icon-maskable-512.png"),
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable",
                },
            ],
            "shortcuts": [
                {"name": _("Kitoblar"), "url": "/kitoblar/"},
                {"name": _("Mening kutubxonam"), "url": "/kitoblar/kutubxonam/"},
            ],
        },
        json_dumps_params={"ensure_ascii": False},
        content_type="application/manifest+json",
    )


@cache_control(max_age=0, no_cache=True)
def service_worker_view(request):
    """Brauzer ichida ishlaydigan skript.

    Ataylab juda sodda qilingan:

    * **Sahifalar (HTML) hech qachon keshlanmaydi.** Aks holda kitob
      narxi o'zgargach foydalanuvchi eski narxni ko'rib qolardi — bu
      do'kon uchun yaramaydi. Internet yo'q bo'lsagina keshdagi
      "oflayn" sahifasi ko'rsatiladi.
    * **CSS, JS va rasmlar keshlanadi.** Ular nomida o'zgarish
      belgisi (hash) bor, ya'ni yangilangani boshqa nom oladi va eski
      keshni ishlatib qo'yish xavfi yo'q.

    Natijada ilova tez ochiladi, lekin ma'lumot doim yangi bo'ladi.
    """
    offline_url = "/oflayn/"
    body = f"""// Avtomatik yaratilgan: apps/core/pwa_views.py ga qarang.
const CACHE = "kutubxona-{CACHE_VERSION}";
const OFFLINE = "{offline_url}";

self.addEventListener("install", (event) => {{
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll([OFFLINE])).then(() => self.skipWaiting())
  );
}});

self.addEventListener("activate", (event) => {{
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
}});

self.addEventListener("fetch", (event) => {{
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Sahifalar: doim tarmoqdan. Tarmoq yo'q bo'lsa - oflayn sahifasi.
  if (request.mode === "navigate") {{
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE)));
    return;
  }}

  // Statik fayllar: keshdan, yo'q bo'lsa tarmoqdan olib keshga qo'yamiz.
  if (url.pathname.startsWith("{settings.STATIC_URL}")) {{
    event.respondWith(
      caches.match(request).then((hit) => {{
        if (hit) return hit;
        return fetch(request).then((response) => {{
          if (response && response.ok) {{
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy));
          }}
          return response;
        }});
      }})
    );
  }}
}});
"""
    return HttpResponse(body, content_type="application/javascript")


def offline_view(request):
    """Internet yo'q bo'lganda ko'rsatiladigan sahifa."""
    return render(request, "core/offline.html")
