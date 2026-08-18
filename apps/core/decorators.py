from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not request.user.role_chosen:
                return redirect("accounts:role_select")
            if request.user.role != role:
                messages.error(request, "Bu sahifaga faqat tegishli rol egalari kira oladi.")
                return redirect("core:home")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def seller_required(view_func):
    return role_required("seller")(view_func)


def buyer_required(view_func):
    return role_required("buyer")(view_func)
