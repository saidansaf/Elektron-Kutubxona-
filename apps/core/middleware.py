from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import translation
from django.utils.translation import gettext as _

THEME_SESSION_KEY = "site_theme"
DEFAULT_THEME = "light"
VALID_THEMES = ("light", "dark")


class UserPreferencesMiddleware:
    """Foydalanuvchining tanlagan mavzusi (dark/light) va tilini qo'llaydi.

    Tizimga kirgan bo'lsa User.theme/User.language maydonlaridan, aks holda
    sessiya/cookie'dan (LocaleMiddleware) olinadi.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Sessiyasi ochiq turgan foydalanuvchi bloklansa, uni darhol chiqaramiz.
        if request.user.is_authenticated and getattr(request.user, "is_blocked", False):
            reason = request.user.blocked_reason
            logout(request)
            messages.error(
                request,
                _("Hisobingiz bloklangan. %(reason)s")
                % {"reason": reason or _("Sabab ko'rsatilmagan.")},
            )
            return redirect("accounts:login")

        theme = None
        if request.user.is_authenticated:
            theme = getattr(request.user, "theme", None)
            user_language = getattr(request.user, "language", None)
            if user_language:
                translation.activate(user_language)
                request.LANGUAGE_CODE = translation.get_language()
        if theme not in VALID_THEMES:
            theme = request.session.get(THEME_SESSION_KEY, DEFAULT_THEME)
        if theme not in VALID_THEMES:
            theme = DEFAULT_THEME
        request.theme = theme
        response = self.get_response(request)
        return response
