from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "settings.py / .env dagi ADMIN_USERNAME va ADMIN_PASSWORD asosida bosh administratorni yaratadi."

    def handle(self, *args, **options):
        username = settings.ADMIN_SEED_USERNAME
        password = settings.ADMIN_SEED_PASSWORD
        email = settings.ADMIN_SEED_EMAIL

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
        else:
            changed = False
            if not user.is_staff or not user.is_superuser:
                user.is_staff = True
                user.is_superuser = True
                changed = True
            if changed:
                user.save()
            self.stdout.write(self.style.WARNING(f"Admin '{username}' allaqachon mavjud edi."))
