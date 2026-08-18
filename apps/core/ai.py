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
import urllib.parse
import urllib.request

from django.conf import settings

TIMEOUT = 45

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

DEFAULT_MODELS = {
    "gemini": "gemini-2.0-flash",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
}

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
    """AI xizmatiga oid xatolar."""


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
        raise AIError(f"AI xizmati xatosi ({exc.code}): {detail}") from exc
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


def chat(messages):
    """Suhbat. `messages` - [{"role": "user"|"assistant", "content": "..."}]."""
    if not is_configured():
        raise AIError(
            "AI kaliti sozlanmagan. .env faylida AI_API_KEY ni to'ldiring "
            "(bepul kalit: https://aistudio.google.com/apikey)."
        )

    provider = active_provider()
    model = settings.AI_MODEL or DEFAULT_MODELS.get(provider, DEFAULT_MODELS["gemini"])

    if provider == "gemini":
        return _chat_gemini(messages, model)
    if provider == "groq":
        return _chat_openai_style(messages, model, "https://api.groq.com/openai/v1/chat/completions")
    if provider == "openrouter":
        return _chat_openai_style(
            messages,
            model,
            "https://openrouter.ai/api/v1/chat/completions",
            {"HTTP-Referer": "http://127.0.0.1:8000", "X-Title": "Elektron Kutubxona"},
        )
    raise AIError(f"Noma'lum AI provayderi: {provider}")


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
