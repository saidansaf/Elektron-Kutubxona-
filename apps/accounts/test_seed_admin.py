"""`seed_admin` buyrug'i: administrator hisobi va parolni tiklash.

Serverda (Render bepul tarifi) terminal yo'q, shuning uchun parolni
tiklashning yagona yo'li — Environment orqali bayroq qo'yib qayta
deploy qilish. Bu yo'l ishlashi shart, aks holda parol unutilsa
administrator hisobiga umuman kirib bo'lmaydi.
"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

User = get_user_model()

ADMIN = {
    "ADMIN_SEED_USERNAME": "Saidansaf",
    "ADMIN_SEED_PASSWORD": "Birinchi-Parol-123",
    "ADMIN_SEED_EMAIL": "admin@kutubxona.uz",
}


@override_settings(**ADMIN, ADMIN_RESET_PASSWORD=False)
class SeedAdminTests(TestCase):
    def run_command(self, **options):
        out = StringIO()
        call_command("seed_admin", stdout=out, **options)
        return out.getvalue()

    def test_hisob_yaratiladi(self):
        self.run_command()

        user = User.objects.get(username="Saidansaf")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("Birinchi-Parol-123"))

    def test_ikkinchi_marta_parol_ozgarmaydi(self):
        self.run_command()

        with override_settings(ADMIN_SEED_PASSWORD="Yangi-Parol-456"):
            self.run_command()

        user = User.objects.get(username="Saidansaf")
        self.assertTrue(user.check_password("Birinchi-Parol-123"))

    def test_reset_password_bayrogi_parolni_yangilaydi(self):
        self.run_command()

        with override_settings(ADMIN_SEED_PASSWORD="Yangi-Parol-456"):
            self.run_command(reset_password=True)

        user = User.objects.get(username="Saidansaf")
        self.assertTrue(user.check_password("Yangi-Parol-456"))

    def test_environment_orqali_ham_tiklanadi(self):
        """Serverda buyruqqa bayroq qo'shib bo'lmaydi — sozlama orqali ham ishlasin."""
        self.run_command()

        with override_settings(
            ADMIN_SEED_PASSWORD="Server-Paroli-789", ADMIN_RESET_PASSWORD=True
        ):
            output = self.run_command()

        user = User.objects.get(username="Saidansaf")
        self.assertTrue(user.check_password("Server-Paroli-789"))
        self.assertIn("o'chirib qo'ying", output)

    def test_huquqlari_olingan_hisob_qaytariladi(self):
        User.objects.create_user(username="Saidansaf", password="x")

        self.run_command()

        user = User.objects.get(username="Saidansaf")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_parolni_tiklash_yoli_korsatiladi(self):
        """Foydalanuvchi nima qilishni bilmay qolmasin."""
        self.run_command()
        output = self.run_command()
        self.assertIn("--reset-password", output)
