"""AI yordamchi xizmati.

Bir nechta bepul provayderni qo'llab-quvvatlaydi - `.env` dagi AI_PROVIDER va
AI_API_KEY qiymatlariga qarab tanlanadi:

    gemini      https://aistudio.google.com/apikey     (bepul, saxiy limit)
    groq        https://console.groq.com/keys          (bepul, juda tez)
    openrouter  https://openrouter.ai/keys             (bepul modellar bor)

Rasm generatsiyasi standart holda Pollinations orqali ishlaydi - u API kalit
talab qilmaydi.
"""

import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 45

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Har bir provayder uchun bir nechta model — birinchisi ishlamasa keyingisi
# sinaladi.
#
# Nega ro'yxat: bepul provayderlar modellarni tez-tez olib tashlaydi
# ("llama-3.3-70b-versatile does not exist"). Bitta nomga bog'lanib qolsak,
# model o'chirilgan kuni AI yordamchi butunlay ishlamay qoladi va sabab
# foydalanuvchiga tushunarsiz bo'ladi.
MODEL_CANDIDATES = {
    "gemini": [
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-1.5-flash",
    ],
    "groq": [
        "llama-3.1-8b-instant",
        "openai/gpt-oss-20b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "qwen/qwen3-32b",
        "llama-3.3-70b-versatile",
    ],
    "openrouter": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-2-9b-it:free",
        "deepseek/deepseek-chat-v3-0324:free",
    ],
}

# Provayderning mavjud modellar ro'yxatini so'rash manzili (xato chiqqanda
# foydalanuvchiga aniq nom ko'rsatish uchun).
MODEL_LIST_URLS = {
    "groq": "https://api.groq.com/openai/v1/models",
    "openrouter": "https://openrouter.ai/api/v1/models",
}

# Ishlagan model shu yerda eslab qolinadi: har so'rovda o'chirilgan
# modellarni qaytadan sinab o'tirmaymiz.
_working_model = {}

SYSTEM_PROMPT = (
    "Sen 'Elektron Kutubxona' saytining yordamchisisan. Sayt elektron kitoblar "
    "bozori: sotuvchilar kitob qo'shadi, xaridorlar sotib oladi, baholaydi va "
    "izoh qoldiradi.\n"
    "Vazifalaring: kitoblar haqida ma'lumot berish, kitob tavsifi (description) "
    "yozish, janr va mualliflar haqida gapirish, kitob tanlashda maslahat berish, "
    "sayt imkoniyatlarini tushuntirish.\n"
    "MUHIM: sen saytga kitob qo'sha olmaysan va hech narsani o'zgartira olmaysan - "
    "buni faqat sotuvchining o'zi qila oladi. Bunday so'rovda qanday qilishni "
    "tushuntir, xolos.\n"
    "Foydalanuvchi qaysi tilda yozsa, o'sha tilda javob ber (o'zbek, rus yoki "
    "ingliz). Javoblaring qisqa va aniq bo'lsin."
)


class AIError(Exception):
    """AI xizmatiga oid xatolar.

    `status` — HTTP kodi (bo'lsa). Model o'chirilganini aniqlash uchun kerak.
    """

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


# Kalitning boshlanishiga qarab provayderni aniqlash. Foydalanuvchi kalitni
# almashtirib, AI_PROVIDER ni o'zgartirishni unutsa ham to'g'ri ishlaydi.
KEY_PREFIXES = (
    ("gsk_", "groq"),
    ("sk-or-", "openrouter"),
    ("AIza", "gemini"),
    ("AQ.", "gemini"),
)


def detect_provider(key):
    """Kalit prefiksidan provayderni topadi. Topilmasa None qaytaradi."""
    for prefix, provider in KEY_PREFIXES:
        if key.startswith(prefix):
            return provider
    return None


def active_provider():
    """Haqiqatda ishlatiladigan provayder.

    Kalitdan aniqlangan provayder .env dagi AI_PROVIDER bilan mos kelmasa,
    kalitnikiga ishonamiz - aks holda so'rov noto'g'ri xizmatga ketardi.
    """
    configured = (settings.AI_PROVIDER or "gemini").lower()
    detected = detect_provider(settings.AI_API_KEY or "")
    return detected or configured


def is_configured():
    return bool(settings.AI_API_KEY)


def _post_json(url, payload, headers=None):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    # User-Agent shart: ba'zi provayderlar (Groq) Cloudflare himoyasi ortida
    # turadi va Python'ning standart imzosini bot deb bloklaydi
    # ("error code: 1010").
    req.add_header("User-Agent", USER_AGENT)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        # Provayderlar xatoni JSON ichida qaytaradi - foydalanuvchiga butun
        # javobni emas, faqat tushunarli qismini ko'rsatamiz.
        detail = raw[:200]
        try:
            body = json.loads(raw)
            err = body.get("error", body)
            if isinstance(err, dict):
                detail = err.get("message") or err.get("detail") or detail
        except (ValueError, AttributeError):
            pass
        raise AIError(f"AI xizmati xatosi ({exc.code}): {detail}", status=exc.code) from exc
    except urllib.error.URLError as exc:
        raise AIError(f"AI xizmatiga ulanib bo'lmadi: {exc.reason}") from exc
    except (ValueError, TimeoutError) as exc:
        raise AIError(f"AI javobini o'qib bo'lmadi: {exc}") from exc


def _chat_gemini(messages, model):
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={urllib.parse.quote(settings.AI_API_KEY)}"
    )
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800},
    }
    data = _post_json(url, payload)
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as exc:
        raise AIError("AI bo'sh javob qaytardi.") from exc


def _chat_openai_style(messages, model, url, extra_headers=None):
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "temperature": 0.7,
        "max_tokens": 800,
    }
    headers = {"Authorization": f"Bearer {settings.AI_API_KEY}"}
    headers.update(extra_headers or {})
    data = _post_json(url, payload, headers)
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise AIError("AI bo'sh javob qaytardi.") from exc


def _is_missing_model(error):
    """Xato "bunday model yo'q" degani anglatadimi.

    Provayderlar buni turlicha qaytaradi: kimdir 404, kimdir 400. Matndagi
    kalit so'zlarga ham qaraymiz — aks holda oddiy kalit xatosini ham model
    xatosi deb o'ylab, barcha modellarni behuda sinab chiqardik.
    """
    text = str(error).lower()
    if error.status not in (400, 404):
        return False
    return any(
        word in text
        for word in ("does not exist", "not found", "decommissioned", "no longer", "unknown model")
    )


def available_models(provider=None, limit=12):
    """Provayderdagi mavjud modellar ro'yxati (xato xabarida ko'rsatish uchun).

    Olib bo'lmasa bo'sh ro'yxat qaytaradi — bu qo'shimcha ma'lumot, bo'lmasa
    ham asosiy xato xabari yetarli.
    """
    provider = provider or active_provider()
    url = MODEL_LIST_URLS.get(provider)
    if not url or not is_configured():
        return []
    try:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {settings.AI_API_KEY}")
        req.add_header("User-Agent", USER_AGENT)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        names = [item.get("id", "") for item in data.get("data", []) if item.get("id")]
        return sorted(names)[:limit]
    except Exception:
        return []


def _send(messages, model, provider):
    """Bitta model bilan bitta urinish."""
    if provider == "gemini":
        return _chat_gemini(messages, model)
    if provider == "groq":
        return _chat_openai_style(messages, model, "https://api.groq.com/openai/v1/chat/completions")
    if provider == "openrouter":
        return _chat_openai_style(
            messages,
            model,
            "https://openrouter.ai/api/v1/chat/completions",
            {"HTTP-Referer": settings.SITE_URL, "X-Title": "Elektron Kutubxona"},
        )
    raise AIError(f"Noma'lum AI provayderi: {provider}")


def models_to_try(provider):
    """Sinab ko'riladigan modellar tartibi."""
    if settings.AI_MODEL:
        # Foydalanuvchi aniq model tanlagan bo'lsa, uni o'zgartirmaymiz.
        return [settings.AI_MODEL]
    candidates = MODEL_CANDIDATES.get(provider) or MODEL_CANDIDATES["gemini"]
    known_good = _working_model.get(provider)
    if known_good and known_good in candidates:
        # Oldingi so'rovda ishlagani birinchi bo'lsin.
        return [known_good] + [m for m in candidates if m != known_good]
    return list(candidates)


def chat(messages):
    """Suhbat. `messages` - [{"role": "user"|"assistant", "content": "..."}].

    Model o'chirilgan bo'lsa keyingisi sinaladi: bepul provayderlar model
    nomlarini tez-tez o'zgartiradi va bitta nomga bog'lanib qolish AI
    yordamchini kutilmaganda ishdan chiqaradi.
    """
    if not is_configured():
        raise AIError(
            "AI kaliti sozlanmagan. .env faylida AI_API_KEY ni to'ldiring "
            "(bepul kalit: https://aistudio.google.com/apikey)."
        )

    provider = active_provider()
    candidates = models_to_try(provider)
    last_error = None

    for model in candidates:
        try:
            answer = _send(messages, model, provider)
        except AIError as exc:
            last_error = exc
            if _is_missing_model(exc):
                logger.warning("Model ishlamadi (%s), keyingisi sinaladi: %s", model, exc)
                continue
            raise
        _working_model[provider] = model
        return answer

    # Hamma model o'chirilgan — foydalanuvchiga aniq nom ko'rsatamiz.
    names = available_models(provider)
    hint = ""
    if names:
        hint = "\n\nMavjud modellar: " + ", ".join(names[:6]) + (
            "\n.env faylida AI_MODEL=<nom> deb yozing."
        )
    raise AIError(f"{last_error}{hint}", status=getattr(last_error, "status", None))


def describe_book(title, author="", genre="", language="uz"):
    """Kitob uchun tavsif yozib beradi."""
    til = {"uz": "o'zbek", "ru": "rus", "en": "ingliz"}.get(language, "o'zbek")
    muallif = author or "noma'lum"
    janr = genre or "ko'rsatilmagan"
    prompt = (
        f"'{title}' nomli kitob uchun sotuv sahifasiga mos tavsif yoz. "
        f"Muallif: {muallif}. Janr: {janr}. "
        f"Tavsif {til} tilida, 3-4 jumla, qiziqarli va ortiqcha maqtovsiz bo'lsin. "
        f"Faqat tavsif matnini qaytar."
    )
    return chat([{"role": "user", "content": prompt}])


def image_url(prompt, width=768, height=1024):
    """Rasm generatsiya qilish uchun manzil qaytaradi.

    Pollinations kalit talab qilmaydi, shuning uchun standart tanlov shu.
    """
    clean = urllib.parse.quote(prompt.strip()[:400])
    return (
        f"https://image.pollinations.ai/prompt/{clean}"
        f"?width={width}&height={height}&nologo=true"
    )
