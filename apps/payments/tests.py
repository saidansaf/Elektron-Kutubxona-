"""To'lov tizimi testlari.

Bu yerda eng muhimi — **pul bilan bog'liq xatolarni oldini olish**.
Shuning uchun testlar "ishladi" degan holatdan ko'ra ko'proq buzilgan
holatlarni tekshiradi: noto'g'ri imzo, noto'g'ri summa, takroriy so'rov,
bekor qilish, begona buyurtma.

Takroriy so'rov alohida ahamiyatga ega: Payme ham, Click ham javobni
olmasa xuddi shu so'rovni qayta yuboradi. Agar kod bunga tayyor
bo'lmasa, foydalanuvchining balansi bir to'lovdan ikki marta oshadi.
"""

import base64
import json
import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Role
from apps.payments import click, payme, services, testmode
from apps.payments.models import Payment, PaymentStatus, Provider

User = get_user_model()

TEST_PAYME_KEY = "payme-test-kaliti-32-belgidan-iborat"
TEST_CLICK_KEY = "click-test-kaliti"

payme_settings = override_settings(
    PAYME_KEY=TEST_PAYME_KEY,
    PAYME_MERCHANT_ID="merchant-1",
    PAYME_ACCOUNT_FIELD="order_id",
)
click_settings = override_settings(
    CLICK_SECRET_KEY=TEST_CLICK_KEY,
    CLICK_SERVICE_ID="service-1",
    CLICK_MERCHANT_ID="merchant-1",
)


class PaymentTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="xaridor", password="Parol-12345", role=Role.BUYER, balance=Decimal("0")
        )

    def make_payment(self, provider=Provider.PAYME, amount="50000"):
        return Payment.objects.create(
            user=self.user, provider=provider, amount=Decimal(amount)
        )

    def balance(self):
        self.user.refresh_from_db()
        return self.user.balance


# ---------------------------------------------------------------- Payme


@payme_settings
class PaymeTests(PaymentTestCase):
    def call(self, method, params, key=TEST_PAYME_KEY):
        header = "Basic " + base64.b64encode(f"Paycom:{key}".encode()).decode()
        return payme.handle({"method": method, "params": params, "id": 1}, header)

    def account(self, payment):
        return {"amount": payment.amount_tiyin, "account": {"order_id": str(payment.pk)}}

    def test_parolsiz_sorov_rad_etiladi(self):
        payment = self.make_payment()
        response = payme.handle(
            {"method": "CheckPerformTransaction", "params": self.account(payment), "id": 1}, ""
        )
        self.assertEqual(response["error"]["code"], payme.ERR_AUTH)

    def test_notogri_parol_rad_etiladi(self):
        payment = self.make_payment()
        response = self.call("CheckPerformTransaction", self.account(payment), key="boshqa-kalit")
        self.assertEqual(response["error"]["code"], payme.ERR_AUTH)

    def test_notanish_metod(self):
        response = self.call("QandaydirMetod", {})
        self.assertEqual(response["error"]["code"], payme.ERR_METHOD_NOT_FOUND)

    def test_buyurtma_topilmasa(self):
        response = self.call(
            "CheckPerformTransaction", {"amount": 100, "account": {"order_id": "999999"}}
        )
        self.assertEqual(response["error"]["code"], payme.ERR_ORDER_NOT_FOUND)

    def test_summa_mos_kelmasa(self):
        payment = self.make_payment()
        params = self.account(payment)
        params["amount"] = 1  # tiyin
        response = self.call("CheckPerformTransaction", params)
        self.assertEqual(response["error"]["code"], payme.ERR_AMOUNT)

    def test_summa_tiyinda_solishtiriladi(self):
        """50 000 so'm = 5 000 000 tiyin. Adashilsa to'lov o'tmaydi."""
        payment = self.make_payment(amount="50000")
        self.assertEqual(payment.amount_tiyin, 5_000_000)
        response = self.call("CheckPerformTransaction", self.account(payment))
        self.assertEqual(response["result"], {"allow": True})

    def test_toliq_oqim_balansni_oshiradi(self):
        payment = self.make_payment()
        self.call("CheckPerformTransaction", self.account(payment))

        params = dict(self.account(payment), id="tx-1", time=int(time.time() * 1000))
        created = self.call("CreateTransaction", params)
        self.assertEqual(created["result"]["state"], payme.STATE_CREATED)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.WAITING)
        self.assertEqual(self.balance(), Decimal("0"))  # hali oshmaydi

        performed = self.call("PerformTransaction", {"id": "tx-1"})
        self.assertEqual(performed["result"]["state"], payme.STATE_PERFORMED)
        self.assertEqual(self.balance(), Decimal("50000"))

    def test_takroriy_perform_balansni_ikki_marta_oshirmaydi(self):
        payment = self.make_payment()
        params = dict(self.account(payment), id="tx-2", time=int(time.time() * 1000))
        self.call("CreateTransaction", params)
        first = self.call("PerformTransaction", {"id": "tx-2"})
        second = self.call("PerformTransaction", {"id": "tx-2"})

        self.assertEqual(self.balance(), Decimal("50000"))
        # Javob ham bir xil bo'lishi kerak, aks holda Payme xato deb hisoblaydi.
        self.assertEqual(first["result"]["perform_time"], second["result"]["perform_time"])

    def test_takroriy_create_bir_xil_javob_beradi(self):
        payment = self.make_payment()
        params = dict(self.account(payment), id="tx-3", time=int(time.time() * 1000))
        first = self.call("CreateTransaction", params)
        second = self.call("CreateTransaction", params)
        self.assertEqual(first["result"], second["result"])

    def test_tolangandan_keyin_bekor_qilinsa_pul_qaytadi(self):
        payment = self.make_payment()
        params = dict(self.account(payment), id="tx-4", time=int(time.time() * 1000))
        self.call("CreateTransaction", params)
        self.call("PerformTransaction", {"id": "tx-4"})
        self.assertEqual(self.balance(), Decimal("50000"))

        cancelled = self.call("CancelTransaction", {"id": "tx-4", "reason": 5})
        self.assertEqual(cancelled["result"]["state"], payme.STATE_CANCELLED_AFTER)
        self.assertEqual(self.balance(), Decimal("0"))

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CANCELLED)
        # Chek ham qolmasligi kerak, aks holda tarixda "to'ldirildi" bo'lib turadi.
        self.assertIsNone(payment.topup)

    def test_tolanmasdan_bekor_qilinsa_holat_minus_bir(self):
        payment = self.make_payment()
        params = dict(self.account(payment), id="tx-5", time=int(time.time() * 1000))
        self.call("CreateTransaction", params)
        cancelled = self.call("CancelTransaction", {"id": "tx-5", "reason": 3})
        self.assertEqual(cancelled["result"]["state"], payme.STATE_CANCELLED)
        self.assertEqual(self.balance(), Decimal("0"))

    def test_tranzaksiya_topilmasa(self):
        response = self.call("PerformTransaction", {"id": "yoq-tranzaksiya"})
        self.assertEqual(response["error"]["code"], payme.ERR_TRANSACTION_NOT_FOUND)

    def test_check_transaction_holatni_qaytaradi(self):
        payment = self.make_payment()
        params = dict(self.account(payment), id="tx-6", time=int(time.time() * 1000))
        self.call("CreateTransaction", params)
        response = self.call("CheckTransaction", {"id": "tx-6"})
        self.assertEqual(response["result"]["state"], payme.STATE_CREATED)
        self.assertEqual(response["result"]["transaction"], str(payment.pk))

    def test_get_statement_tolovlarni_beradi(self):
        payment = self.make_payment()
        now = int(time.time() * 1000)
        self.call("CreateTransaction", dict(self.account(payment), id="tx-7", time=now))
        response = self.call("GetStatement", {"from": now - 10_000, "to": now + 10_000})
        ids = [row["id"] for row in response["result"]["transactions"]]
        self.assertIn("tx-7", ids)

    def test_bir_buyurtma_ikki_marta_tolanmaydi(self):
        payment = self.make_payment()
        params = dict(self.account(payment), id="tx-8", time=int(time.time() * 1000))
        self.call("CreateTransaction", params)
        self.call("PerformTransaction", {"id": "tx-8"})

        # Payme yangi tranzaksiya ochmoqchi bo'lsa, ruxsat berilmasligi kerak.
        response = self.call("CheckPerformTransaction", self.account(payment))
        self.assertEqual(response["error"]["code"], payme.ERR_CANNOT_PERFORM)

    def test_webhook_manzili_ishlaydi(self):
        payment = self.make_payment()
        header = "Basic " + base64.b64encode(f"Paycom:{TEST_PAYME_KEY}".encode()).decode()
        response = self.client.post(
            reverse("payments:payme_webhook"),
            data=json.dumps(
                {"method": "CheckPerformTransaction", "params": self.account(payment), "id": 1}
            ),
            content_type="application/json",
            headers={"authorization": header},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], {"allow": True})

    def test_buzuq_json_500_bermaydi(self):
        """Xato JSON kelsa ham 200 qaytishi kerak, aks holda Payme cheksiz urinadi."""
        response = self.client.post(
            reverse("payments:payme_webhook"), data="{buzuq", content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["error"]["code"], payme.ERR_PARSE)


# ---------------------------------------------------------------- Click


@click_settings
class ClickTests(PaymentTestCase):
    def base(self, payment, **extra):
        data = {
            "click_trans_id": "12345",
            "service_id": "service-1",
            "click_paydoc_id": "999",
            "merchant_trans_id": str(payment.pk),
            "amount": f"{payment.amount:.2f}",
            "error": 0,
            "error_note": "",
            "sign_time": "2026-08-20 12:00:00",
        }
        data.update(extra)
        return data

    def call(self, data, action, sign=True):
        data = dict(data, action=action)
        data["sign_string"] = (
            click.make_sign(data, action) if sign else "0" * 32
        )
        return click.handle(data)

    def test_notogri_imzo_rad_etiladi(self):
        payment = self.make_payment(Provider.CLICK)
        response = self.call(self.base(payment), click.ACTION_PREPARE, sign=False)
        self.assertEqual(response["error"], click.ERR_SIGN)
        self.assertEqual(self.balance(), Decimal("0"))

    def test_prepare_va_complete_balansni_oshiradi(self):
        payment = self.make_payment(Provider.CLICK)
        prepared = self.call(self.base(payment), click.ACTION_PREPARE)
        self.assertEqual(prepared["error"], click.OK)
        self.assertEqual(prepared["merchant_prepare_id"], payment.pk)
        self.assertEqual(self.balance(), Decimal("0"))  # hali oshmaydi

        data = self.base(payment, merchant_prepare_id=payment.pk)
        completed = self.call(data, click.ACTION_COMPLETE)
        self.assertEqual(completed["error"], click.OK)
        self.assertEqual(self.balance(), Decimal("50000"))

    def test_takroriy_complete_balansni_ikki_marta_oshirmaydi(self):
        payment = self.make_payment(Provider.CLICK)
        self.call(self.base(payment), click.ACTION_PREPARE)
        data = self.base(payment, merchant_prepare_id=payment.pk)
        self.call(data, click.ACTION_COMPLETE)
        self.call(data, click.ACTION_COMPLETE)
        self.assertEqual(self.balance(), Decimal("50000"))

    def test_summa_mos_kelmasa(self):
        payment = self.make_payment(Provider.CLICK)
        response = self.call(self.base(payment, amount="1.00"), click.ACTION_PREPARE)
        self.assertEqual(response["error"], click.ERR_AMOUNT)

    def test_click_xato_bilan_kelsa_bekor_qilinadi(self):
        payment = self.make_payment(Provider.CLICK)
        self.call(self.base(payment), click.ACTION_PREPARE)
        data = self.base(
            payment, merchant_prepare_id=payment.pk, error=-9, error_note="Cancelled"
        )
        response = self.call(data, click.ACTION_COMPLETE)

        self.assertEqual(response["error"], click.ERR_CANCELLED)
        self.assertEqual(self.balance(), Decimal("0"))
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CANCELLED)

    def test_yoq_buyurtma(self):
        data = {
            "click_trans_id": "1",
            "service_id": "service-1",
            "merchant_trans_id": "999999",
            "amount": "50000.00",
            "error": 0,
            "sign_time": "2026-08-20 12:00:00",
        }
        response = self.call(data, click.ACTION_PREPARE)
        self.assertEqual(response["error"], click.ERR_TRANSACTION_NOT_FOUND)

    def test_notanish_action(self):
        payment = self.make_payment(Provider.CLICK)
        response = click.handle(dict(self.base(payment), action=7))
        self.assertEqual(response["error"], click.ERR_ACTION)

    def test_webhook_manzili_ishlaydi(self):
        payment = self.make_payment(Provider.CLICK)
        data = dict(self.base(payment), action=click.ACTION_PREPARE)
        data["sign_string"] = click.make_sign(data, click.ACTION_PREPARE)
        response = self.client.post(reverse("payments:click_webhook"), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["error"], click.OK)


# ---------------------------------------------------------------- Sayt


class SiteFlowTests(PaymentTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_toldirish_sahifasi_ochiladi(self):
        response = self.client.get(reverse("accounts:topup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payme")
        self.assertContains(response, "Click")

    def test_karta_raqami_sorlmaydi(self):
        """Karta ma'lumotlari bizga umuman kelmasligi kerak."""
        response = self.client.get(reverse("accounts:topup"))
        self.assertNotContains(response, 'name="card_number"')

    def test_tolov_boshlanadi_va_yonaltiriladi(self):
        response = self.client.post(
            reverse("payments:start"), {"amount": "50000", "provider": "payme"}
        )
        payment = Payment.objects.get()
        self.assertEqual(payment.amount, Decimal("50000.00"))
        self.assertRedirects(
            response, "http://testserver" + reverse("payments:test_checkout", args=[payment.pk])
        )
        self.assertEqual(self.balance(), Decimal("0"))

    def test_juda_kichik_summa_rad_etiladi(self):
        self.client.post(reverse("payments:start"), {"amount": "10", "provider": "payme"})
        self.assertFalse(Payment.objects.exists())

    def test_sinov_sahifasida_tolash(self):
        self.client.post(reverse("payments:start"), {"amount": "50000", "provider": "payme"})
        payment = Payment.objects.get()

        self.client.post(
            reverse("payments:test_checkout", args=[payment.pk]), {"action": "pay"}
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertEqual(self.balance(), Decimal("50000"))

    def test_sinov_sahifasida_bekor_qilish(self):
        self.client.post(reverse("payments:start"), {"amount": "50000", "provider": "click"})
        payment = Payment.objects.get()

        self.client.post(
            reverse("payments:test_checkout", args=[payment.pk]), {"action": "cancel"}
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CANCELLED)
        self.assertEqual(self.balance(), Decimal("0"))

    def test_begona_buyurtmaga_kirib_bolmaydi(self):
        other = User.objects.create_user(username="boshqa", password="Parol-12345")
        payment = Payment.objects.create(
            user=other, provider=Provider.PAYME, amount=Decimal("50000")
        )
        response = self.client.get(reverse("payments:test_checkout", args=[payment.pk]))
        self.assertEqual(response.status_code, 404)

    @override_settings(PAYMENT_MODE="live")
    def test_jonli_rejimda_sinov_sahifasi_yopiq(self):
        """Aks holda haqiqiy pulsiz balans to'ldirib olish mumkin bo'lardi."""
        payment = self.make_payment()
        response = self.client.post(
            reverse("payments:test_checkout", args=[payment.pk]), {"action": "pay"}
        )
        self.assertRedirects(response, reverse("accounts:topup"))
        self.assertEqual(self.balance(), Decimal("0"))

    def test_tolov_tarixi(self):
        self.make_payment()
        response = self.client.get(reverse("payments:history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "50000")

    def test_kirmagan_foydalanuvchi_tolov_boshlay_olmaydi(self):
        self.client.logout()
        self.client.post(reverse("payments:start"), {"amount": "50000", "provider": "payme"})
        self.assertFalse(Payment.objects.exists())


# ---------------------------------------------------------------- Test rejimi


class TestModeTests(PaymentTestCase):
    """Sinov rejimi haqiqiy protokol kodidan o'tishi kerak.

    Aks holda Payme/Click kodi hech qachon ishlamaydi va kalit kelgan
    kuni xatolar birinchi marta jonli to'lovda chiqadi.
    """

    def test_payme_oqimi_tranzaksiya_yaratadi(self):
        payment = self.make_payment(Provider.PAYME)
        testmode.simulate_success(payment)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)
        # Tranzaksiya ID protokol orqali yozilgan bo'lishi kerak.
        self.assertTrue(payment.transaction_id)
        self.assertEqual(self.balance(), Decimal("50000"))

    def test_click_oqimi_imzodan_otadi(self):
        payment = self.make_payment(Provider.CLICK)
        testmode.simulate_success(payment)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertEqual(self.balance(), Decimal("50000"))

    def test_bekor_qilish(self):
        payment = self.make_payment(Provider.PAYME)
        testmode.simulate_cancel(payment)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CANCELLED)
        self.assertEqual(self.balance(), Decimal("0"))

    @override_settings(PAYMENT_MODE="live", PAYME_MERCHANT_ID="m1", PAYME_KEY="k1")
    def test_jonli_rejimda_havola_paymega_ketadi(self):
        payment = self.make_payment(Provider.PAYME)
        link = services.checkout_link(payment, "https://kutubxona.uz")
        self.assertIn("checkout.paycom.uz", link)
        # Manzil base64 ichida buyurtma raqami va tiyindagi summa bo'lishi kerak.
        encoded = link.rsplit("/", 1)[-1]
        decoded = base64.b64decode(encoded).decode()
        self.assertIn(f"ac.order_id={payment.pk}", decoded)
        self.assertIn(f"a={payment.amount_tiyin}", decoded)

    @override_settings(
        PAYMENT_MODE="live",
        CLICK_SERVICE_ID="s1",
        CLICK_MERCHANT_ID="m1",
        CLICK_SECRET_KEY="k1",
    )
    def test_jonli_rejimda_havola_clickka_ketadi(self):
        payment = self.make_payment(Provider.CLICK)
        link = services.checkout_link(payment, "https://kutubxona.uz")
        self.assertIn("my.click.uz", link)
        self.assertIn(f"transaction_param={payment.pk}", link)

    @override_settings(PAYMENT_MODE="live", PAYME_MERCHANT_ID="", PAYME_KEY="")
    def test_sozlanmagan_tizim_korinmaydi(self):
        self.assertNotIn(Provider.PAYME, services.available_providers())
