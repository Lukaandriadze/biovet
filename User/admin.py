from django.contrib import admin

from .models import EmailVerificationCode


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "attempts", "created_at")
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at",)
