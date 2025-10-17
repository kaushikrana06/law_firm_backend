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

def validate_phone_12(value: str) -> None:
    digits = value[1:] if value.startswith("+") else value
    if not digits.isdigit() or len(digits) != 12:
        raise ValidationError(
            "Phone must be exactly 12 digits (country code included); optional leading '+'."
        )


def _generate_human_code(name: str) -> str:
    base = re.sub(r"[^A-Za-z]", "", (name or "")).upper()
    prefix = (base[:3] or "CLT").ljust(3, "X")
    suffix = uuid.uuid4().hex[-6:].upper()
    return f"{prefix}-{suffix}"

class Firm(models.Model):
    name = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Client(models.Model):
    name = models.CharField(max_length=30)
    code = models.CharField(max_length=32, unique=True, blank=True)
    phone = models.CharField(max_length=13, validators=[validate_phone_12])
    email = models.EmailField(unique=True)
    attorney = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clients",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code or 'NO-CODE'})"

    def save(self, *args, **kwargs):
        validate_phone_12(self.phone)
        if not self.code:
            candidate = _generate_human_code(self.name)
            while Client.objects.filter(code=candidate).exists():
                candidate = _generate_human_code(self.name)
            self.code = candidate
        super().save(*args, **kwargs)


class Case(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="cases")
    firm = models.ForeignKey(Firm, on_delete=models.PROTECT, related_name="cases")

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
        ]
        ordering = ["-last_update"]

    def __str__(self) -> str:
        return f"Case {self.pk} - {self.client.name}"

    @property
    def attorney(self):
        return self.client.attorney
    
    
# on_delete=models.CASCADE