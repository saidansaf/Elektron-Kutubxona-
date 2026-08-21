from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "provider", "amount", "status", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("user__username", "transaction_id")
    readonly_fields = ("created_at", "updated_at")
