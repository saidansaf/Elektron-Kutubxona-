from django import template

register = template.Library()


@register.filter
def liked(book, user):
    """Foydalanuvchi kitobni yoqtirganmi: {% if book|liked:user %}"""
    return book.liked_by(user)


@register.filter
def liked_obj(obj, user):
    """Izoh yoki javob yoqtirilganmi: {% if review|liked_obj:user %}"""
    return obj.liked_by(user)


@register.filter
def stars(value):
    try:
        rating = round(float(value))
    except (TypeError, ValueError):
        rating = 0
    rating = max(0, min(5, rating))
    return "★" * rating + "☆" * (5 - rating)


@register.filter
def money(value):
    """Summani mingliklarga ajratib ko'rsatadi: 580000 -> "580 000".

    Ajratgich sifatida uzilmaydigan probel ishlatiladi, shunda son
    satr oxirida ikkiga bo'linib ketmaydi.
    """
    try:
        amount = int(round(float(value or 0)))
    except (TypeError, ValueError):
        return value
    return f"{amount:,}".replace(",", " ")
