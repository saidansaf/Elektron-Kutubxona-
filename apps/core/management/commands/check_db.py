"""Ma'lumotlar bazasi sozlamalarini tekshiradi.

    python manage.py check_db

Qaysi baza ishlatilayotgani, server javob berayotgani, baza va foydalanuvchi
mavjudligini ketma-ket tekshirib, muammo qayerdaligini aytadi.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = "Baza sozlamalari va ulanishini tekshiradi."

    def handle(self, *args, **options):
        ok = self.style.SUCCESS
        bad = self.style.ERROR
        warn = self.style.WARNING

        db = settings.DATABASES["default"]
        engine = db["ENGINE"]
        is_sqlite = "sqlite" in engine

        # 1. .env va tanlangan baza
        self.stdout.write("1) Sozlama")
        env_path = Path(settings.BASE_DIR) / ".env"
        if env_path.exists():
            self.stdout.write(ok(f"   .env topildi: {env_path}"))
            for line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                if line.strip().startswith("USE_SQLITE"):
                    self.stdout.write(f"   .env dagi qator: {line.strip()}")
                    break
            else:
                self.stdout.write(warn("   .env da USE_SQLITE qatori yo'q (standart: PostgreSQL)"))
        else:
            self.stdout.write(warn(f"   .env topilmadi: {env_path}"))

        if is_sqlite:
            self.stdout.write(ok("   Ishlatilayotgan baza: SQLite"))
            self.stdout.write(f"   Fayl: {db['NAME']}")
        else:
            self.stdout.write(ok("   Ishlatilayotgan baza: PostgreSQL"))
            self.stdout.write(f"   Host: {db['HOST']}:{db['PORT']}")
            self.stdout.write(f"   Baza: {db['NAME']}   Foydalanuvchi: {db['USER']}")

        # 2. Ulanish
        self.stdout.write("\n2) Ulanish")
        try:
            conn = connections["default"]
            conn.ensure_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception as exc:
            self.stdout.write(bad(f"   ULANIB BO'LMADI:\n   {exc}"))
            if not is_sqlite:
                self._postgres_hint(db, warn)
            return

        self.stdout.write(ok("   Ulandi va so'rov bajarildi."))

        # 3. Jadvallar
        self.stdout.write("\n3) Jadvallar")
        try:
            table_names = connections["default"].introspection.table_names()
        except Exception as exc:
            self.stdout.write(bad(f"   O'qib bo'lmadi: {exc}"))
            return

        if "books_book" in table_names and "accounts_user" in table_names:
            self.stdout.write(ok(f"   {len(table_names)} ta jadval bor - migratsiyalar bajarilgan."))
        elif table_names:
            self.stdout.write(warn(f"   {len(table_names)} ta jadval bor, lekin loyihaniki yo'q."))
            self.stdout.write(warn("   `python manage.py migrate` ni bajaring."))
        else:
            self.stdout.write(warn("   Bo'sh - `python manage.py migrate` ni bajaring."))
            return

        # 4. Ma'lumotlar
        self.stdout.write("\n4) Ma'lumotlar")
        from django.contrib.auth import get_user_model

        from apps.books.models import Book

        User = get_user_model()
        self.stdout.write(f"   Foydalanuvchilar: {User.objects.count()}")
        self.stdout.write(f"   Kitoblar: {Book.objects.count()}")
        if not User.objects.filter(is_superuser=True).exists():
            self.stdout.write(warn("   Administrator yo'q - `python manage.py seed_admin` ni bajaring."))

        self.stdout.write(ok("\nHammasi joyida."))

    def _postgres_hint(self, db, warn):
        self.stdout.write(warn("\n   Tekshiring:"))
        self.stdout.write(warn("   1. PostgreSQL xizmati ishlayaptimi?"))
        self.stdout.write(warn("      Windows: Xizmatlar (services.msc) -> postgresql-x64-NN -> Ishga tushirish"))
        self.stdout.write(warn(f"   2. '{db['NAME']}' bazasi va '{db['USER']}' foydalanuvchisi yaratilganmi?"))
        self.stdout.write(warn("      `python manage.py setup_db` buyrug'i ularni yaratib beradi."))
        self.stdout.write(warn("   3. .env dagi DB_PASSWORD to'g'rimi?"))
        self.stdout.write(warn("\n   PostgreSQL'siz ishlash uchun .env da USE_SQLITE=True qiling."))
