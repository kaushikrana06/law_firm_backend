from __future__ import annotations
import re
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

CASE_TYPES = (
    "Auto Accident",
    "Work Injury",
    "Slip and Fall",
    "Medical Negligence",
    "Product Liability",
)

CASE_STATUSES = (
    "Case Approved",
    "Case Signed",
    "Court Date Scheduled",
    "Documents Received",
    "Hearing Scheduled",
    "Insurance Contacted",
    "Mediation Scheduled",
    "Pending Insurance Response",
    "Settlement Approved",
    "Treatment Scheduled",
)

CASE_TYPE_CHOICES = tuple((v, v) for v in CASE_TYPES)
CASE_STATUS_CHOICES = tuple((v, v) for v in CASE_STATUSES)

def validate_phone_10(value: str) -> None:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 10:
        raise ValidationError("Phone must be exactly 10 digits.")
    
def _generate_human_code(name: str) -> str:
    base = re.sub(r"[^A-Za-z]", "", (name or "")).upper()
    prefix = (base[:3] or "CLT").ljust(3, "X")
    suffix = uuid.uuid4().hex[-6:].upper()
    return f"{prefix}-{suffix}"

class Case(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    client_name = models.CharField(max_length=30)
    client_code = models.CharField(max_length=32, blank=True) 
    client_phone = models.CharField(max_length=10, validators=[validate_phone_10])
    client_email = models.EmailField()

    firm_name = models.CharField(max_length=30)
    attorney = models.ForeignKey(  # dropdown in admin
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cases",
    )
    attorney_name = models.CharField(max_length=50, blank=True)  

    # Case metadata
    case_type = models.CharField(max_length=32, choices=CASE_TYPE_CHOICES)
    case_status = models.CharField(max_length=32, choices=CASE_STATUS_CHOICES)
    date_opened = models.DateTimeField(default=timezone.now)
    last_update = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["case_type"]),
            models.Index(fields=["case_status"]),
            models.Index(fields=["date_opened"]),
            models.Index(fields=["last_update"]),
            models.Index(fields=["client_name"]),
            models.Index(fields=["client_email"]),
            models.Index(fields=["client_code"]),
            models.Index(fields=["firm_name"]),
            models.Index(fields=["attorney"]),
        ]
        ordering = ["-last_update"]

    def __str__(self) -> str:
        return f"Case {self.pk} - {self.client_name}"

    def clean(self):
        if self.last_update and self.date_opened and self.last_update < self.date_opened:
            raise ValidationError({"last_update": "Last update cannot be before date opened."})

      
        qs = Case.objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        conflict = qs.filter(client_email=self.client_email).exclude(attorney_id=self.attorney_id).exists()
        if conflict:
            raise ValidationError({"attorney": "This client email is already associated with another attorney."})

        if self.client_code:
            conflict_code = qs.filter(client_code=self.client_code).exclude(attorney_id=self.attorney_id).exists()
            if conflict_code:
                raise ValidationError({"attorney": "This client code is already associated with another attorney."})

    def save(self, *args, **kwargs):
        validate_phone_10(self.client_phone)
        if not self.client_code:
            existing = (
                Case.objects
                .filter(client_email=self.client_email)
                .order_by("-last_update")
                .first()
            )
            self.client_code = existing.client_code if existing and existing.client_code else _generate_human_code(self.client_name)

        super().save(*args, **kwargs)
