import csv, io, re
from datetime import datetime
from typing import List, Tuple
from django import forms
from django.urls import path, reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.http import JsonResponse


from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.utils.html import strip_tags

from django.http import HttpResponse  # you use HttpResponse below
from django.middleware.csrf import get_token  # to render a valid CSRF token
from .models import Case, CASE_TYPES, CASE_STATUSES , CaseNote # you reference these
from django.forms.models import BaseInlineFormSet


class RequiredCaseNoteInlineFormSet(BaseInlineFormSet):
    """
    Require at least one CaseNote with a status (not deleted) for each Case.
    """
    def clean(self):
        super().clean()

        has_status = False

        for form in self.forms:
            # Skip forms that didn't validate
            if not hasattr(form, "cleaned_data"):
                continue

            # Skip forms marked for deletion
            if form.cleaned_data.get("DELETE", False):
                continue

            status = form.cleaned_data.get("status")
            status_note = form.cleaned_data.get("status_note")
            existing_id = form.cleaned_data.get("id")

            # Ignore completely empty extra rows
            if not status and not status_note and not existing_id:
                continue

            if status:
                has_status = True
                break

        if not has_status:
            raise forms.ValidationError(
                "At least one case status (in Case Notes) is required."
            )

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

class CaseCsvImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV file",
        help_text="Headers: Client Name, Phone, Email, Firm Name, Case Type, Case Status, Date Opened, Notes" " (optional: Firm Email, Firm Phone)",
    )
    validate_only = forms.BooleanField(required=False, initial=False, label="Dry run (validate only)")

    def clean_csv_file(self):
        f = self.cleaned_data["csv_file"]
        if not (getattr(f, "name", "") or "").lower().endswith(".csv"):
            raise forms.ValidationError("Only .csv files are allowed.")
        return f
class CaseNoteInline(admin.TabularInline):
    model = CaseNote
    formset = RequiredCaseNoteInlineFormSet
    extra = 1
    readonly_fields = ("created_at", "updated_at")
    fields = ("status", "status_note", "created_at","updated_at")  # <- ADD THIS

    
@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    inlines = [CaseNoteInline]

    list_display = (
        "id",   
        "client_name", "client_code", "client_email", "client_phone",
        "attorney",
        "firm_name", "firm_email", "firm_phone",
        "case_type", "case_status",
        "date_opened", "last_update",
    )
    list_filter = ("attorney", "case_type", "case_status", "date_opened")
    search_fields = (
        "id",
        "client_name", "client_email", "client_code", "client_phone",
        "firm_name", "firm_email", "firm_phone",
        "notes",
        "attorney__username", "attorney__email",
    )
    autocomplete_fields = ("attorney",)
    readonly_fields = ("last_update",)
    exclude = ("client_code","attorney_name","case_status")  
    change_list_template = "admin/cases/case/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("import-csv/", self.admin_site.admin_view(self.import_csv_view), name="cases_case_import_csv"),
        ]
        return custom + urls

    def import_csv_view(self, request):
        """
        AJAX endpoint used by the changelist modal to validate/import a CSV.
        Detects duplicates (in-file and in-DB) and reports them.
        """
        from django.http import JsonResponse
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1"
        if request.method != "POST" or not is_ajax:
            return JsonResponse({"ok": False, "errors": [{"row": None, "msg": "Use the modal to upload via AJAX."}]}, status=405)

        form = CaseCsvImportForm(request.POST, request.FILES)
        if not form.is_valid():
            errs = []
            for field, msgs in form.errors.items():
                for m in msgs:
                    errs.append({"row": None, "msg": f"{field}: {m}"})
            return JsonResponse({"ok": False, "errors": errs or [{"row": None, "msg": "Invalid form"}]}, status=400)

        f = form.cleaned_data["csv_file"]
        validate_only = form.cleaned_data["validate_only"]

        # Decode file
        try:
            text = f.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return JsonResponse({"ok": False, "errors": [{"row": None, "msg": "CSV must be UTF-8 encoded."}]}, status=400)

        import csv, io, re
        from datetime import datetime
        from django.utils import timezone

        reader = csv.DictReader(io.StringIO(text))
        required = ["Client Name", "Phone", "Email", "Firm Name", "Case Type", "Case Status", "Date Opened", "Notes"]
        missing = [h for h in required if h not in (reader.fieldnames or [])]
        if missing:
            return JsonResponse({"ok": False, "errors": [{"row": None, "msg": f"Missing header(s): {', '.join(missing)}"}]}, status=400)

        valid_types = set(CASE_TYPES)
        valid_stats = set(CASE_STATUSES)

        def make_key(name, phone, email, firm, ctype, cstat, opened_dt):
            return (
                (name or "").strip().lower(),
                re.sub(r"\D", "", phone or ""),
                (email or "").strip().lower(),
                (firm or "").strip().lower(),
                (ctype or "").strip(),
                (cstat or "").strip(),
                opened_dt.date().isoformat() if opened_dt else "",
            )

        created_candidates = []   # [{"obj": Case, "row": int, "key": tuple}]
        errors = []
        seen_in_file = set()
        file_dupes = []

        rownum = 1  # header = row 1
        for row in reader:
            rownum += 1
            name  = (row.get("Client Name") or "").strip()
            phone = re.sub(r"\D", "", (row.get("Phone") or ""))
            email = (row.get("Email") or "").strip()
            firm  = (row.get("Firm Name") or "").strip()
            ctype = (row.get("Case Type") or "").strip()
            cstat = (row.get("Case Status") or "").strip()
            dopen = (row.get("Date Opened") or "").strip()
            notes = (row.get("Notes") or "").strip()
            status_note_csv = (
                row.get("Status Note")
                or row.get("Status_note")
                or row.get("status_note")
            )
            status_note_csv = status_note_csv.strip()
            # NEW: optional firm contacts
            firm_email = (row.get("Firm Email") or "").strip()                 # NEW
            firm_phone = re.sub(r"\D", "", (row.get("Firm Phone") or ""))      # NEW

            row_err = []
            if not name: row_err.append("Client Name required")
            if len(phone) != 10: row_err.append("Phone must be 10 digits")
            if not email: row_err.append("Email required")
            if not firm: row_err.append("Firm Name required")
            if ctype not in valid_types: row_err.append(f"Case Type must be one of: {', '.join(sorted(valid_types))}")
            if cstat not in valid_stats: row_err.append(f"Case Status must be one of: {', '.join(sorted(valid_stats))}")

            # NEW: validate firm_phone only if provided
            if firm_phone and len(firm_phone) != 10:
                row_err.append("Firm Phone must be 10 digits if provided")     # NEW

            try:
                opened = datetime.strptime(dopen, "%Y-%m-%d") if dopen else timezone.now()
            except ValueError:
                try:
                    opened = datetime.fromisoformat(dopen)
                except Exception:
                    row_err.append("Date Opened must be YYYY-MM-DD or ISO 8601")
                    opened = None

            if row_err:
                errors.append({"row": rownum, "msg": "; ".join(row_err)})
                continue

            key = make_key(name, phone, email, firm, ctype, cstat, opened)
            if key in seen_in_file:
                file_dupes.append({"row": rownum, "msg": "Duplicate row in the uploaded CSV"})
                continue
            seen_in_file.add(key)

            obj = Case(
                client_name=name,
                client_phone=phone,
                client_email=email,
                firm_name=firm,
                firm_email=firm_email,     # NEW
                firm_phone=firm_phone,     # NEW
                case_type=ctype,
                case_status=cstat,
                date_opened=opened,
                notes=notes,
            )
            obj.attorney_id = None
            obj._status_note_csv = status_note_csv

            created_candidates.append({"obj": obj, "row": rownum, "key": key})

        if errors:
            return JsonResponse({"ok": False, "errors": errors}, status=400)

        # Check duplicates in DB (email case-insensitive, date by date part)
        db_dupes = []
        to_save = []
        for item in created_candidates:
            o = item["obj"]
            exists = Case.objects.filter(
                client_name=o.client_name,
                client_phone=o.client_phone,
                firm_name=o.firm_name,
                case_type=o.case_type,
                case_status=o.case_status,
                date_opened__date=o.date_opened.date(),
            ).filter(client_email__iexact=o.client_email).exists()

            if exists:
                db_dupes.append({"row": item["row"], "msg": "Duplicate of an existing case in the database"})
            else:
                to_save.append(o)

        if validate_only:
            return JsonResponse({
                "ok": True,
                "validated": True,
                "count": len(to_save),
                "skipped_duplicates_in_file": len(file_dupes),
                "skipped_duplicates_in_db": len(db_dupes),
                "duplicates": file_dupes + db_dupes,
            })

        for o in to_save:
            o.save()
            status_note_text = getattr(o, "_status_note_csv", "").strip()
            if not status_note_text:
                # Fallback to main case.notes if no explicit status_note column
                status_note_text = (o.notes or "").strip()

            if status_note_text:
                # This uses your Case.add_status_note, which:
                # - finds or creates a CaseNote for (case, status)
                # - updates its status_note text
                o.add_status_note(
                    status_note_text,
                    status=o.case_status,
                    created_by=None,  # CSV import, no specific user
                )

        return JsonResponse({
            "ok": True,
            "created": len(to_save),
            "skipped_duplicates_in_file": len(file_dupes),
            "skipped_duplicates_in_db": len(db_dupes),
            "duplicates": file_dupes + db_dupes,
        })

    def save_related(self, request, form, formsets, change):
        """
        After saving the Case and its inlines, sync case.case_status
        to the latest CaseNote.status (if any).
        """
        super().save_related(request, form, formsets, change)

        obj = form.instance  # this is the Case
        latest_note = obj.status_notes.order_by("-created_at").first()
        if latest_note and obj.case_status != latest_note.status:
            obj.case_status = latest_note.status
            obj.save(update_fields=["case_status", "last_update"])


    @admin.action(description="Resend client access email")
    def resend_client_access_email(self, request, queryset):
        count = 0
        for case in queryset:
            _send_client_case_created_email(case=case)
            count += 1
        self.message_user(request, _(f"Resent access email for {count} case(s)."), level=messages.SUCCESS)

    # actions = ["resend_client_access_email"]

    
