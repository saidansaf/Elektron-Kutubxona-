"""AI sozlamalarini tekshiradi.

    python manage.py check_ai

.env fayli topilganmi, kalit o'qilganmi va provayder javob beradimi -
hammasini ketma-ket tekshirib, muammo qayerdaligini aytadi.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core import ai


class Command(BaseCommand):
    help = "AI kaliti va provayderi to'g'ri sozlanganini tekshiradi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-request",
            action="store_true",
            help="Provayderga haqiqiy so'rov yubormaslik (faqat sozlamalarni tekshirish).",
        )

    def handle(self, *args, **options):
        ok = self.style.SUCCESS
        bad = self.style.ERROR
        warn = self.style.WARNING

        # 1. .env fayli
        env_path = Path(settings.BASE_DIR) / ".env"
        self.stdout.write("1) .env fayli")
        if env_path.exists():
            self.stdout.write(ok(f"   topildi: {env_path}"))
            has_line = any(
                line.strip().startswith("AI_API_KEY")
                for line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            )
            if has_line:
                self.stdout.write(ok("   AI_API_KEY qatori bor"))
            else:
                self.stdout.write(bad("   AI_API_KEY qatori YO'Q - faylga qo'shing"))
        else:
            self.stdout.write(bad(f"   TOPILMADI: {env_path}"))
            self.stdout.write(warn("   .env.example nusxasini .env nomi bilan saqlang."))
            return

        # 2. Kalit o'qildimi
        self.stdout.write("\n2) Kalit")
        key = settings.AI_API_KEY
        if key:
            masked = f"{key[:6]}...{key[-4:]}" if len(key) > 12 else "(juda qisqa)"
            self.stdout.write(ok(f"   o'qildi: {masked}  (uzunligi {len(key)})"))
        else:
            self.stdout.write(bad("   BO'SH - Django kalitni ko'rmayapti"))
            self.stdout.write(warn("   Sabablari: server qayta ishga tushirilmagan,"))
            self.stdout.write(warn("   yoki kalit .env emas, .env.example ga yozilgan."))
            return

        # 3. Provayder
        self.stdout.write("\n3) Provayder")
        configured = settings.AI_PROVIDER
        detected = ai.detect_provider(key)
        provider = ai.active_provider()
        known = ("gemini", "groq", "openrouter")

        if detected and detected != configured:
            self.stdout.write(
                warn(f"   .env da AI_PROVIDER={configured}, lekin kalit {detected} ga tegishli.")
            )
            self.stdout.write(warn(f"   Kalitga ishonamiz -> {detected} ishlatiladi."))
            self.stdout.write(warn(f"   Chalkashmaslik uchun .env da AI_PROVIDER={detected} qilib qo'ying."))
        elif not detected:
            self.stdout.write(warn("   Kalit prefiksi tanish emas, .env dagi qiymat ishlatiladi."))

        if provider in known:
            models = ai.models_to_try(provider)
            if settings.AI_MODEL:
                self.stdout.write(ok(f"   {provider} (model: {settings.AI_MODEL})"))
            else:
                self.stdout.write(ok(f"   {provider} (model: {models[0]})"))
                if len(models) > 1:
                    self.stdout.write(f"   Zaxira: {', '.join(models[1:])}")
        else:
            self.stdout.write(bad(f"   noma'lum: '{provider}'"))
            self.stdout.write(warn(f"   AI_PROVIDER quyidagilardan biri bo'lsin: {', '.join(known)}"))
            return

        if options["no_request"]:
            return

        # 4. Jonli so'rov
        self.stdout.write("\n4) Sinov so'rovi")
        try:
            answer = ai.chat([{"role": "user", "content": "Javob sifatida faqat 'ishladi' deb yoz."}])
        except ai.AIError as exc:
            self.stdout.write(bad(f"   XATO: {exc}"))
            self.stdout.write(warn("\n   Ko'p uchraydigan sabablar:"))
            self.stdout.write(warn("   - 400/403: kalit noto'g'ri yoki bekor qilingan"))
            self.stdout.write(warn("   - 404: model o'chirilgan (provayderlar tez-tez almashtiradi)"))
            self.stdout.write(warn("   - 429: bepul limit tugagan, biroz kutib qayta urinib ko'ring"))

            # Provayderning o'zidan mavjud modellarni so'raymiz - taxmin
            # qilib o'tirmasdan aniq nomni ko'rsatish uchun.
            names = ai.available_models(provider)
            if names:
                self.stdout.write("\n   Hozir mavjud modellar:")
                for name in names:
                    self.stdout.write(f"     {name}")
                self.stdout.write(warn("\n   .env ga yozing:  AI_MODEL=<yuqoridagilardan biri>"))
            return

        self.stdout.write(ok(f"   javob keldi: {answer[:80]}"))
        self.stdout.write(ok("\nHammasi joyida - AI ishlayapti."))
