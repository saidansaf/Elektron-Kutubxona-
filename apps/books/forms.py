from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Author, Book, Genre, Reply, Review


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = (
            "title",
            "author",
            "genre",
            "language",
            "pages",
            "price",
            "publish_year",
            "description",
            "cover",
            "file",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, seller=None, **kwargs):
        super().__init__(*args, **kwargs)
        if seller is not None:
            self.fields["author"].queryset = Author.objects.all()
        self.fields["genre"].required = False
        self.fields["genre"].empty_label = "Janr tanlanmagan"


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ("full_name", "bio", "birth_date", "photo")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
            "birth_date": forms.DateInput(attrs={"type": "date"}),
        }


class GenreForm(forms.ModelForm):
    class Meta:
        model = Genre
        fields = ("name",)


class CheckoutForm(forms.Form):
    """Sotib olish sahifasi.

    Karta ma'lumotlari bu yerda so'ralmaydi: to'lov Payme yoki Click
    sahifasida amalga oshiriladi, balansda pul yetsa esa umuman karta
    kerak emas. Ilgari bu yerda karta raqami va muddati so'ralardi, lekin
    ular hech qayerga yuborilmasdi — endi bunday soxta maydon yo'q.
    """

    address = forms.CharField(
        label=_("Uy manzili"),
        widget=forms.TextInput(attrs={"placeholder": _("Shahar, ko'cha, uy raqami")}),
    )


class ReplyForm(forms.ModelForm):
    """Izohga javob. Javobga javob yozib bo'lmaydi - faqat bitta daraja."""

    class Meta:
        model = Reply
        fields = ("text",)
        widgets = {
            "text": forms.TextInput(attrs={"placeholder": _("Javob yozing...")}),
        }
        labels = {"text": ""}


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {
            "rating": forms.RadioSelect(choices=[(i, f"{i} ⭐") for i in range(1, 6)]),
            "comment": forms.Textarea(attrs={"rows": 3, "placeholder": _("Fikringiz (ixtiyoriy)")}),
        }


#: Katalogni saralash variantlari: qiymat -> (ko'rinadigan nom, tartiblash maydonlari)
SORT_OPTIONS = {
    "new": (_("Avval yangilari"), ("-created_at",)),
    "old": (_("Avval eskilari"), ("created_at",)),
    "cheap": (_("Avval arzoni"), ("price", "-created_at")),
    "expensive": (_("Avval qimmati"), ("-price", "-created_at")),
    "rating": (_("Reyting bo'yicha"), ("-avg_rating", "-created_at")),
    "popular": (_("Ommabopligi bo'yicha"), ("-sales_total", "-created_at")),
}
DEFAULT_SORT = "new"


class BookFilterForm(forms.Form):
    q = forms.CharField(required=False, label=_("Qidiruv"))
    language = forms.ChoiceField(required=False, choices=[("", _("Barcha tillar"))])
    genre = forms.ModelChoiceField(
        required=False, queryset=Genre.objects.all(), empty_label=_("Barcha janrlar"), label=_("Janr")
    )
    author = forms.ModelChoiceField(
        required=False, queryset=Author.objects.all(), empty_label=_("Barcha mualliflar"), label=_("Muallif")
    )
    min_price = forms.DecimalField(required=False, label=_("Narx (dan)"))
    max_price = forms.DecimalField(required=False, label=_("Narx (gacha)"))
    sort = forms.ChoiceField(
        required=False,
        label=_("Saralash"),
        choices=[(key, label) for key, (label, _fields) in SORT_OPTIONS.items()],
    )

    def __init__(self, *args, **kwargs):
        from django.conf import settings

        super().__init__(*args, **kwargs)
        self.fields["language"].label = _("Til")
        self.fields["language"].choices = [("", _("Barcha tillar"))] + list(settings.BOOK_LANGUAGES)
