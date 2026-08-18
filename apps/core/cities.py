"""Ob-havo uchun davlatlar va shaharlar ro'yxati.

Nega tayyor ro'yxat, geokodlash API'si emas:

  * Bitta tashqi xizmatga kamroq bog'liqlik. Ro'yxat o'zgarmaydi, shuning
    uchun uni har safar internetdan so'rashning ma'nosi yo'q.
  * Tanlash darrov ishlaydi — foydalanuvchi yozayotganda kutib turmaydi.
  * Shahar nomlari o'zbekcha yoziladi (Moskva, Qohira), API esa ularni
    inglizcha qaytarardi.

Koordinatalar shahar markazi bo'yicha, uchta o'nlik xona yetarli
(taxminan 100 metr aniqlik — ob-havo uchun ortig'i kerak emas).

Ro'yxat sayt (ob-havo sahifasi) va Telegram bot uchun bitta manba.
"""

# {davlat: [(shahar, kenglik, uzunlik), ...]}
COUNTRIES = {
    "O'zbekiston": [
        ("Toshkent", 41.311, 69.240),
        ("Samarqand", 39.627, 66.975),
        ("Buxoro", 39.767, 64.423),
        ("Andijon", 40.783, 72.333),
        ("Namangan", 40.998, 71.671),
        ("Farg'ona", 40.386, 71.787),
        ("Qarshi", 38.860, 65.789),
        ("Nukus", 42.460, 59.617),
        ("Urganch", 41.550, 60.631),
        ("Termiz", 37.224, 67.278),
        ("Jizzax", 40.116, 67.842),
        ("Guliston", 40.489, 68.786),
        ("Navoiy", 40.084, 65.379),
    ],
    "Rossiya": [
        ("Moskva", 55.756, 37.617),
        ("Sankt-Peterburg", 59.939, 30.316),
        ("Novosibirsk", 55.031, 82.921),
        ("Yekaterinburg", 56.839, 60.605),
        ("Qozon", 55.796, 49.106),
        ("Samara", 53.195, 50.101),
        ("Vladivostok", 43.116, 131.882),
    ],
    "Qozog'iston": [
        ("Almati", 43.238, 76.889),
        ("Ostona", 51.169, 71.449),
        ("Shimkent", 42.318, 69.596),
        ("Aqtobe", 50.284, 57.166),
    ],
    "Qirg'iziston": [
        ("Bishkek", 42.874, 74.570),
        ("O'sh", 40.529, 72.796),
    ],
    "Tojikiston": [
        ("Dushanbe", 38.560, 68.787),
        ("Xujand", 40.283, 69.633),
    ],
    "Turkmaniston": [
        ("Ashxobod", 37.950, 58.383),
        ("Turkmanobod", 39.073, 63.578),
    ],
    "Turkiya": [
        ("Istanbul", 41.008, 28.978),
        ("Anqara", 39.933, 32.859),
        ("Antalya", 36.897, 30.713),
        ("Izmir", 38.423, 27.143),
    ],
    "BAA": [
        ("Dubay", 25.205, 55.271),
        ("Abu-Dabi", 24.453, 54.377),
        ("Sharja", 25.346, 55.421),
    ],
    "Saudiya Arabistoni": [
        ("Riyod", 24.713, 46.675),
        ("Makka", 21.389, 39.857),
        ("Madina", 24.524, 39.569),
        ("Jidda", 21.486, 39.192),
    ],
    "AQSH": [
        ("Nyu-York", 40.713, -74.006),
        ("Vashington", 38.907, -77.037),
        ("Los-Anjeles", 34.052, -118.244),
        ("Chikago", 41.878, -87.630),
    ],
    "Buyuk Britaniya": [
        ("London", 51.507, -0.128),
        ("Manchester", 53.481, -2.242),
    ],
    "Germaniya": [
        ("Berlin", 52.520, 13.405),
        ("Myunxen", 48.135, 11.582),
        ("Frankfurt", 50.111, 8.682),
    ],
    "Fransiya": [
        ("Parij", 48.857, 2.352),
        ("Lion", 45.764, 4.836),
    ],
    "Janubiy Koreya": [
        ("Seul", 37.567, 126.978),
        ("Busan", 35.180, 129.076),
    ],
    "Xitoy": [
        ("Pekin", 39.904, 116.407),
        ("Shanxay", 31.230, 121.474),
        ("Guanchjou", 23.129, 113.264),
    ],
    "Yaponiya": [
        ("Tokio", 35.690, 139.692),
        ("Osaka", 34.694, 135.502),
    ],
    "Hindiston": [
        ("Dehli", 28.614, 77.209),
        ("Mumbay", 19.076, 72.878),
    ],
    "Misr": [
        ("Qohira", 30.044, 31.236),
    ],
    "Malayziya": [
        ("Kuala-Lumpur", 3.139, 101.687),
    ],
}

DEFAULT_COUNTRY = "O'zbekiston"
DEFAULT_CITY = "Toshkent"


def as_json_data():
    """Shablonga (JavaScript'ga) uzatish uchun qulay ko'rinish."""
    return {
        country: [{"name": name, "lat": lat, "lon": lon} for name, lat, lon in cities]
        for country, cities in COUNTRIES.items()
    }


def find_city(name):
    """Shahar nomi bo'yicha (davlat, shahar, kenglik, uzunlik) qaytaradi.

    Katta-kichik harf va yon bo'shliqlarga e'tibor bermaydi — bot'da
    foydalanuvchi qo'lda yozishi mumkin.
    """
    needle = (name or "").strip().casefold()
    if not needle:
        return None
    for country, cities in COUNTRIES.items():
        for city, lat, lon in cities:
            if city.casefold() == needle:
                return country, city, lat, lon
    return None


def search_cities(query, limit=8):
    """Nomi ichida `query` uchraydigan shaharlar (bot qidiruvi uchun)."""
    needle = (query or "").strip().casefold()
    if not needle:
        return []
    found = []
    for country, cities in COUNTRIES.items():
        for city, lat, lon in cities:
            if needle in city.casefold():
                found.append((country, city, lat, lon))
                if len(found) >= limit:
                    return found
    return found
