"""
Admin setup so an admin can create Firms, Clients, and Cases
and automatically email the client their code and link — no extra files.
"""

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.utils.html import strip_tags

from .models import Firm, Client, Case

User = get_user_model()


def _send_client_case_created_email(*, client: Client, case: Case) -> None:
    login_url = getattr(settings, "FRONTEND_URL", "")  
    ctx = {
        "client_name": client.name,
        "client_code": client.code,
        "login_url": login_url,
        "firm": case.firm.name,
        "case_type": case.case_type,
        "case_status": case.case_status,
    }

    subject = "Your case access code"

    try:
        html = render_to_string("email/client_code_only.html", ctx)
    except TemplateDoesNotExist:
        button_html = (
            f"<p style='margin:16px 0'>"
            f"<a href='{login_url}' "
            f"style='display:inline-block;padding:10px 16px;border-radius:6px;"
            f"text-decoration:none;border:1px solid #333'>Go to Login</a>"
            f"</p>"
            if login_url else ""
        )
        html = (
            f"<p>Hi {client.name},</p>"
            f"<p>Your case has been created at <strong>{case.firm.name}</strong>.</p>"
            f"<p><strong>Your Code:</strong> <code>{client.code}</code></p>"
            f"<p>Use this code on the login page to view your case status.</p>"
            f"{button_html}"
            f"<hr>"
            f"<p style='font-size:12px;color:#666'>"
            f"Case Type: {case.case_type} &nbsp;|&nbsp; Status: {case.case_status}"
            f"</p>"
        )

    text = strip_tags(html)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[client.email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)

@admin.register(Firm)
class FirmAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "email", "phone", "attorney")
    list_filter = ("attorney",)
    search_fields = ("name", "email", "phone", "code", "attorney__email", "attorney__username")
    autocomplete_fields = ("attorney",)
    exclude = ("code",)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "attorney":
            kwargs["queryset"] = User.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.action(description="Resend client access email")
def resend_client_access_email(modeladmin, request, queryset):
    count = 0
    for case in queryset:
        _send_client_case_created_email(client=case.client, case=case)
        count += 1
    messages.success(request, _(f"Resent access email for {count} case(s)."))


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "firm", "case_type", "case_status", "date_opened", "last_update")
    list_filter = ("firm", "case_type", "case_status", "date_opened")
    search_fields = ("id", "client__name", "client__email", "client__code", "notes")
    autocomplete_fields = ("client", "firm")
    readonly_fields = ("last_update",)
    # actions = [resend_client_access_email]

    # def save_model(self, request, obj: Case, form, change):
    #     super().save_model(request, obj, form, change)
    #     if not change:
    #         _send_client_case_created_email(client=obj.client, case=obj)

    
