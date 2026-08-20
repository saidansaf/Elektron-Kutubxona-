"""Tezlikka bevosita ta'sir qiladigan sozlamalar testi.

Bular "sayt sekin" muammosining kod tomonidagi qismi: javoblar
siqilishi va xizmatni uyg'oq ushlab turish uchun arzon `/ping/`
sahifasi bo'lishi kerak.
"""

from django.test import TestCase
from django.urls import reverse


class PingTest(TestCase):
    """Uyg'otish uchun ishlatiladigan eng arzon sahifa."""

    def test_ping_ok_qaytaradi(self):
        response = self.client.get(reverse("core:ping"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_ping_bazaga_murojaat_qilmaydi(self):
        """Uyg'otish so'rovi bazani bezovta qilmasin.

        Sabab: uxlab qolmasin deb har 10 daqiqada chaqiriladigan manzil
        bazaga ham yuk bermasligi kerak - aks holda "tezlashtiraman" deb
        aksincha qilib qo'yiladi.
        """
        with self.assertNumQueries(0):
            self.client.get(reverse("core:ping"))


class GzipTest(TestCase):
    """HTML javoblari siqilishi kerak."""

    def test_bosh_sahifa_siqiladi(self):
        response = self.client.get(
            reverse("core:home"),
            headers={"accept-encoding": "gzip"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Encoding"), "gzip")

    def test_siqishni_qollamaydigan_brauzerga_oddiy_javob(self):
        response = self.client.get(reverse("core:home"), headers={"accept-encoding": ""})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Content-Encoding", response.headers)
