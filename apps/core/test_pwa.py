"""Saytni telefonga ilova qilib o'rnatish (PWA) uchun testlar.

Bu yerda tekshiriladigan narsalar brauzer talab qiladigan shartlar:
manifest to'g'ri, service worker saytning ildizidan beriladi va
sahifalar keshlanmaydi.
"""

import json

from django.test import TestCase
from django.urls import reverse


class ManifestTests(TestCase):
    def test_manifest_ochiladi(self):
        response = self.client.get(reverse("manifest"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/manifest+json")

    def test_ornatish_uchun_zarur_maydonlar_bor(self):
        """Brauzer shu maydonlarsiz "o'rnatish" taklifini ko'rsatmaydi."""
        data = json.loads(self.client.get(reverse("manifest")).content)

        self.assertTrue(data["name"])
        self.assertTrue(data["short_name"])
        self.assertEqual(data["start_url"], "/")
        self.assertEqual(data["display"], "standalone")
        self.assertTrue(data["theme_color"].startswith("#"))

    def test_belgilar_192_va_512_bor(self):
        """Android aynan shu ikki o'lchamni so'raydi."""
        data = json.loads(self.client.get(reverse("manifest")).content)
        sizes = {icon["sizes"] for icon in data["icons"]}

        self.assertIn("192x192", sizes)
        self.assertIn("512x512", sizes)

    def test_maskable_belgi_bor(self):
        """Usiz Android belgini oq kvadrat ichiga solib qo'yadi."""
        data = json.loads(self.client.get(reverse("manifest")).content)
        purposes = {icon.get("purpose") for icon in data["icons"]}

        self.assertIn("maskable", purposes)

    def test_nom_tanlangan_tilda(self):
        response = self.client.get(reverse("manifest"), headers={"accept-language": "ru"})
        data = json.loads(response.content)

        self.assertEqual(data["lang"], "ru")


class ServiceWorkerTests(TestCase):
    def test_sayt_ildizidan_beriladi(self):
        """Manzil `/sw.js` bo'lishi SHART.

        Service worker faqat o'zi turgan papkadan pastdagi manzillarni
        boshqara oladi. `/static/js/sw.js` da tursa butun saytga ta'sir
        qila olmaydi va ilova o'rnatilmaydi.
        """
        self.assertEqual(reverse("service_worker"), "/sw.js")

        response = self.client.get("/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response["Content-Type"])

    def test_fetch_hodisasi_bor(self):
        """Brauzer `fetch` ishlovchisi yo'q worker'ni "ilova" deb sanamaydi."""
        body = self.client.get("/sw.js").content.decode()
        self.assertIn('addEventListener("fetch"', body)

    def test_sahifalar_keshlanmaydi(self):
        """Sahifa keshlansa kitob narxi eskirib qolardi.

        Faqat statik fayllar keshlanadi; HTML doim tarmoqdan olinadi.
        """
        body = self.client.get("/sw.js").content.decode()

        self.assertIn('request.mode === "navigate"', body)
        self.assertIn("fetch(request).catch", body)

    def test_workerning_ozi_keshlanmaydi(self):
        """Aks holda yangi versiya foydalanuvchiga hech qachon yetib bormaydi."""
        response = self.client.get("/sw.js")
        self.assertIn("no-cache", response["Cache-Control"])


class OfflineTests(TestCase):
    def test_oflayn_sahifasi_ochiladi(self):
        response = self.client.get(reverse("offline"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/offline.html")


class HeaderTests(TestCase):
    """Tepadagi tasmadagi uchta narsa: qidiruv, til va o'rnatish tugmasi."""

    def test_qidiruv_katalogga_yuboradi(self):
        html = self.client.get(reverse("core:home")).content.decode()

        self.assertIn('class="header-search"', html)
        self.assertIn(f'action="{reverse("books:catalog")}"', html)
        self.assertIn('name="q"', html)

    def test_qidiruv_ishlaydi(self):
        response = self.client.get(reverse("books:catalog"), {"q": "kitob"})
        self.assertEqual(response.status_code, 200)

    def test_til_tugmalari_mehmonga_ham_korinadi(self):
        html = self.client.get(reverse("core:home")).content.decode()

        self.assertIn("lang-switch", html)
        self.assertEqual(html.count('name="language"'), 3)

    def test_ornatish_tugmasi_korinadi(self):
        html = self.client.get(reverse("core:home")).content.decode()
        self.assertIn('id="installBtn"', html)

    def test_qolda_ornatish_yoriqnomasi_bor(self):
        """Safari va Firefox avtomatik taklif bermaydi.

        O'sha brauzerlarda tugma bosilganda qo'lda o'rnatish yo'riqnomasi
        ochilishi kerak - aks holda tugma hech narsa qilmagandek tuyuladi.
        """
        html = self.client.get(reverse("core:home")).content.decode()

        self.assertIn('id="installHelp"', html)
        self.assertIn("Safari", html)

    def test_manifest_sahifaga_ulangan(self):
        html = self.client.get(reverse("core:home")).content.decode()
        self.assertIn('rel="manifest"', html)
