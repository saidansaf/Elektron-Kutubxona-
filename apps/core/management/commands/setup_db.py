"""PostgreSQL bazasi va foydalanuvchisini yaratadi.

psql.exe ni qidirish shart emas - psycopg2 orqali to'g'ridan-to'g'ri ulanadi.

    python manage.py setup_db
"""

import getpass

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.db.postgresql.base import _decode


class Command(BaseCommand):
    help = ".env dagi sozlamalar asosida PostgreSQL bazasi va foydalanuvchisini yaratadi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--superuser",
            default="postgres",
            help="PostgreSQL administrator nomi (standart: postgres).",
        )
        parser.add_argument(
            "--superpassword",
            default=None,
            help="Administrator paroli. Ko'rsatilmasa, so'raladi.",
        )

    def handle(self, *args, **options):
        try:
            import psycopg2
            from psycopg2 import sql
        except ImportError as exc:  # pragma: no cover
            raise CommandError("psycopg2 o'rnatilmagan: pip install -r requirements.txt") from exc

        db = settings.DATABASES["default"]
        if "postgresql" not in db["ENGINE"]:
            raise CommandError(
                "Loyiha hozir PostgreSQL'ga sozlanmagan.\n"
                ".env faylida USE_SQLITE=False qilib, qaytadan urinib ko'ring."
            )

        name = db["NAME"]
        user = db["USER"]
        password = db["PASSWORD"]
        host = db["HOST"] or "127.0.0.1"
        port = db["PORT"] or "5432"

        superuser = options["superuser"]
        superpassword = options["superpassword"]
        if superpassword is None:
            superpassword = getpass.getpass(f"'{superuser}' foydalanuvchisining paroli: ")

        self.stdout.write(f"{host}:{port} manzilidagi PostgreSQL'ga ulanmoqda...")
        try:
            conn = psycopg2.connect(
                dbname="postgres",
                user=superuser,
                password=superpassword,
                host=host,
                port=port,
            )
        except UnicodeDecodeError as exc:
            raise CommandError(
                "Ulanib bo'lmadi.\n\nPostgreSQL javobi: "
                + _decode(getattr(exc, "object", b"")).strip()
            ) from exc
        except Exception as exc:
            raise CommandError(f"Ulanib bo'lmadi.\n\n{exc}") from exc

        conn.autocommit = True  # CREATE DATABASE tranzaksiya ichida ishlamaydi
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [user])
                if cur.fetchone():
                    self.stdout.write(self.style.WARNING(f"'{user}' foydalanuvchisi allaqachon mavjud."))
                else:
                    cur.execute(
                        sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(user)),
                        [password],
                    )
                    self.stdout.write(self.style.SUCCESS(f"'{user}' foydalanuvchisi yaratildi."))

                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", [name])
                if cur.fetchone():
                    self.stdout.write(self.style.WARNING(f"'{name}' bazasi allaqachon mavjud."))
                else:
                    cur.execute(
                        sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8'").format(
                            sql.Identifier(name), sql.Identifier(user)
                        )
                    )
                    self.stdout.write(self.style.SUCCESS(f"'{name}' bazasi yaratildi."))

                cur.execute(
                    sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                        sql.Identifier(name), sql.Identifier(user)
                    )
                )
        finally:
            conn.close()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Tayyor. Endi quyidagilarni bajaring:"))
        self.stdout.write("    python manage.py migrate")
        self.stdout.write("    python manage.py seed_admin")
        self.stdout.write("    python manage.py runserver")
