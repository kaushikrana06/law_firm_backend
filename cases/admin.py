from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.utils.html import strip_tags

from .models import Case

User = get_user_model()

def _send_client_case_created_email(*, case: Case) -> None:
    # login_url = getattr(settings, "FRONTEND_URL", "")
    # ctx = {
    #     "client_name": case.client_name,
    #     "client_code": case.client_code,
    #     "login_url": login_url,
    #     "firm": case.firm_name,
    #     "case_type": case.case_type,
    #     "case_status": case.case_status,
    # }

    # subject = "Your case access code"

    # try:
    #     html = render_to_string("email/client_code_only.html", ctx)
    # except TemplateDoesNotExist:
    #     button_html = (
    #         f"<p style='margin:16px 0'>"
    #         f"<a href='{login_url}' "
    #         f"style='display:inline-block;padding:10px 16px;border-radius:6px;"
    #         f"text-decoration:none;border:1px solid #333'>Go to Login</a>"
    #         f"</p>"
    #         if login_url else ""
    #     )
    #     html = (
    #         f"<p>Hi {case.client_name},</p>"
    #         f"<p>Your case has been created at <strong>{case.firm_name}</strong>.</p>"
    #         f"<p><strong>Your Code:</strong> <code>{case.client_code}</code></p>"
    #         f"<p>Use this code on the login page to view your case status.</p>"
    #         f"{button_html}"
    #         f"<hr>"
    #         f"<p style='font-size:12px;color:#666'>"
    #         f"Case Type: {case.case_type} &nbsp;|&nbsp; Status: {case.case_status}"
    #         f"</p>"
    #     )

    # text = strip_tags(html)
    # msg = EmailMultiAlternatives(
    #     subject=subject,
    #     body=text,
    #     from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
    #     to=[case.client_email],
    # )
    # msg.attach_alternative(html, "text/html")
    # msg.send(fail_silently=False)
    return

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client_name", "client_code", "client_email", "client_phone",
        "attorney",
        "firm_name",
        "case_type", "case_status",
        "date_opened", "last_update",
    )
    list_filter = ("attorney", "case_type", "case_status", "date_opened")
    search_fields = (
        "id",
        "client_name", "client_email", "client_code", "client_phone",
        "firm_name", "notes",
        "attorney__username", "attorney__email",
    )
    autocomplete_fields = ("attorney",)
    readonly_fields = ("last_update",)
    exclude = ("client_code","attorney_name")  

    # Optional action to resend the access email
    @admin.action(description="Resend client access email")
    def resend_client_access_email(self, request, queryset):
        count = 0
        for case in queryset:
            _send_client_case_created_email(case=case)
            count += 1
        self.message_user(request, _(f"Resent access email for {count} case(s)."), level=messages.SUCCESS)

    # actions = ["resend_client_access_email"]

    
