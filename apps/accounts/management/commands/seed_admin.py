"""Bosh administratorni yaratadi yoki parolini yangilaydi.

    python manage.py seed_admin                    # yo'q bo'lsa yaratadi
    python manage.py seed_admin --reset-password   # parolni majburan yangilaydi

`.env` (yoki serverdagi Environment) dagi ADMIN_USERNAME va ADMIN_PASSWORD
ishlatiladi.

Nega `--reset-password` kerak: ilgari bu buyruq parolni faqat hisob
birinchi marta yaratilganda o'rnatardi. Ya'ni serverdagi ADMIN_PASSWORD
o'zgartirilsa ham parol eskiligicha qolaverardi va foydalanuvchi
"parolni almashtirdim, lekin kirmayapti" degan holatga tushardi.
Render'ning bepul tarifida "Shell" yo'qligi sababli parolni boshqa yo'l
bilan tiklashning ham imkoni yo'q edi.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "ADMIN_USERNAME/ADMIN_PASSWORD asosida bosh administratorni yaratadi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Hisob mavjud bo'lsa ham parolni ADMIN_PASSWORD ga tenglashtiradi.",
        )

    def handle(self, *args, **options):
        username = settings.ADMIN_SEED_USERNAME
        password = settings.ADMIN_SEED_PASSWORD
        email = settings.ADMIN_SEED_EMAIL

        # Serverda buyruqqa bayroq qo'shib bo'lmaydi (build skripti bitta),
        # shuning uchun Environment orqali ham yoqish mumkin.
        reset = options["reset_password"] or settings.ADMIN_RESET_PASSWORD

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )

        if created:
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Admin '{username}' yaratildi."))
            return

        changed = []
        if not user.is_staff or not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            changed.append("huquqlar")
        if reset:
            user.set_password(password)
            changed.append("parol")

        if changed:
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"Admin '{username}' yangilandi: {', '.join(changed)}.")
            )
            if "parol" in changed:
                self.stdout.write(
                    self.style.WARNING(
                        "Parol yangilandi. ADMIN_RESET_PASSWORD ni endi o'chirib qo'ying —\n"
                        "aks holda har deploydan keyin parol qaytadan tiklanaveradi."
                    )
                )
        else:
            self.stdout.write(self.style.WARNING(f"Admin '{username}' allaqachon mavjud edi."))
            self.stdout.write(
                "Parolni yangilash uchun: seed_admin --reset-password\n"
                "yoki serverda ADMIN_RESET_PASSWORD=1 qo'yib qayta deploy qiling."
            )
