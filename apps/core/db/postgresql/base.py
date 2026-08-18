"""PostgreSQL backend ustidan yupqa qobiq - ulanish xatolarini o'qiladigan qiladi.

Rus/o'zbek tilidagi Windows'da libpq ulanish xatosini tizim kodlashida (odatda
cp1251) qaytaradi. psycopg2 uni UTF-8 deb o'qishga urinadi va natijada asl
sababni butunlay yashiradigan `UnicodeDecodeError` chiqadi:

    UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc2 ...

Bu yerda o'sha xatoni ushlab, xabarning xom baytlarini mos kodlashda ochamiz va
foydalanuvchiga nima qilish kerakligini aytamiz.
"""

from django.db.backends.postgresql import base as postgresql_base
from django.db.utils import OperationalError

# libpq xabari qaysi kodlashlarda kelishi mumkinligi (birinchi mos kelgani olinadi).
FALLBACK_ENCODINGS = ("cp1251", "cp1252", "cp866", "latin-1")

HINT = (
    "\n\nTekshiring:\n"
    "  1. PostgreSQL xizmati ishlayaptimi?\n"
    "  2. '{name}' bazasi va '{user}' foydalanuvchisi yaratilganmi?\n"
    "     CREATE USER {user} WITH PASSWORD '...';\n"
    "     CREATE DATABASE {name} OWNER {user};\n"
    "  3. .env dagi DB_USER / DB_PASSWORD / DB_HOST / DB_PORT to'g'rimi?\n"
    "\nPostgreSQL'siz sinab ko'rish uchun .env da USE_SQLITE=True qiling."
)


def _decode(raw):
    """Xom baytlarni mos kodlashda matnga o'giradi."""
    if not isinstance(raw, (bytes, bytearray)):
        return str(raw)
    for encoding in FALLBACK_ENCODINGS:
        try:
            return bytes(raw).decode(encoding)
        except UnicodeDecodeError:
            continue
    return bytes(raw).decode("utf-8", errors="replace")


class DatabaseWrapper(postgresql_base.DatabaseWrapper):
    def get_new_connection(self, conn_params):
        try:
            return super().get_new_connection(conn_params)
        except UnicodeDecodeError as exc:
            # exc.object - libpq qaytargan xom bayt xabari.
            message = _decode(getattr(exc, "object", b"")).strip()
            settings = self.settings_dict
            raise OperationalError(
                "PostgreSQL'ga ulanib bo'lmadi.\n\nPostgreSQL javobi: "
                + (message or "(xabar o'qib bo'lmadi)")
                + HINT.format(
                    name=settings.get("NAME") or "kutubxona_db",
                    user=settings.get("USER") or "kutubxona_user",
                )
            ) from exc
