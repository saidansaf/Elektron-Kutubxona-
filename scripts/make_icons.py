"""Ilova belgilarini (PWA ikonkalari) yasaydi.

Nega skript: telefonga o'rnatiladigan ilovaga PNG belgilar kerak —
brauzerlar SVG'ni hamma joyda qabul qilmaydi. Belgilar `static/img/`
ichida saqlanadi va bir marta yasab qo'yiladi; rang yoki shakl
o'zgarsa shu skriptni qayta ishga tushirish kifoya:

    python scripts/make_icons.py

Shakl `static/img/favicon.svg` bilan bir xil: ko'k-turkuaz gradient
ustida ochiq kitob.
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw

OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "static" / "img"

# favicon.svg dagi gradient to'xtashlari
GRADIENT = ((0x0B, 0x5E, 0x9E), (0x12, 0xA5, 0xC8), (0x22, 0xD3, 0xD9))

# Chetlari silliq chiqishi uchun avval katta qilib chizamiz, keyin kichraytiramiz.
SUPERSAMPLE = 4


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


def _gradient(size: int) -> Image.Image:
    """Chapdan o'ngga, yuqoridan pastga qiya gradient."""
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    start, middle, end = GRADIENT
    for y in range(size):
        for x in range(size):
            # Diagonal bo'ylab 0..1
            t = (x + y) / (2 * (size - 1))
            pixels[x, y] = _lerp(start, middle, t / 0.55) if t <= 0.55 else _lerp(
                middle, end, (t - 0.55) / 0.45
            )
    return image


def _draw_book(draw: ImageDraw.ImageDraw, size: int) -> None:
    """64x64 tarmoqdagi o'lchamlarni joriy o'lchamga ko'chiradi."""

    def s(value: float) -> float:
        return value * size / 64

    radius = s(3)
    # Chap sahifa - oppoq, o'ng sahifa - biroz ko'kish (hajm hissi uchun)
    draw.rounded_rectangle([s(13), s(17), s(30.4), s(47)], radius=radius, fill=(255, 255, 255))
    draw.rounded_rectangle([s(33.6), s(17), s(51), s(47)], radius=radius, fill=(232, 246, 253))
    # Muqova (o'rtadagi chok)
    draw.rounded_rectangle([s(30.2), s(16), s(33.8), s(48)], radius=s(1.4), fill=(9, 74, 126))


def make_icon(size: int, inset: float = 0.0) -> Image.Image:
    """Bitta belgi yasaydi.

    `inset` - "maskable" belgilar uchun: Android belgini dumaloq qilib
    kesib olishi mumkin, shuning uchun rasm chetdan ichkariroq chiziladi.
    """
    big = size * SUPERSAMPLE
    background = _gradient(big)

    # Burchaklarni yumaloqlaymiz
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big - 1, big - 1], radius=big * 14 / 64, fill=255)

    icon = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    icon.paste(background, (0, 0), mask)

    if inset:
        inner = round(big * (1 - 2 * inset))
        book = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
        _draw_book(ImageDraw.Draw(book), inner)
        icon.alpha_composite(book, (round(big * inset), round(big * inset)))
    else:
        _draw_book(ImageDraw.Draw(icon), big)

    return icon.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = [
        ("icon-192.png", 192, 0.0),
        ("icon-512.png", 512, 0.0),
        # Maskable: rasm 12% ichkariroq — Android uni dumaloq kessa ham kitob butun qoladi.
        ("icon-maskable-512.png", 512, 0.12),
        # Telefon ekranida yorliq sifatida (Apple)
        ("apple-touch-icon.png", 180, 0.0),
    ]
    for name, size, inset in targets:
        image = make_icon(size, inset)
        path = OUT_DIR / name
        image.save(path, "PNG", optimize=True)
        print(f"{path.relative_to(OUT_DIR.parent.parent)}  {size}x{size}")


if __name__ == "__main__":
    main()
