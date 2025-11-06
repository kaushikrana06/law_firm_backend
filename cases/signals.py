# cases/signals.py
from typing import List

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Case
from notifications.services import notify_client_case_updated


@receiver(pre_save, sender=Case)
def case_status_or_notes_changed(sender, instance: Case, **kwargs) -> None:
    """
    Detect changes to case_status or notes and trigger a client notification.

    This runs for *every* Case save:
      - If instance.pk is None => it's a new case, skip.
      - Otherwise, compare with previous DB version.
    """
    if not instance.pk:
        # New case, nothing to compare against
        return

    try:
        previous = Case.objects.get(pk=instance.pk)
    except Case.DoesNotExist:
        # Shouldn't happen in practice, but be defensive
        return

    changed: List[str] = []

    if previous.case_status != instance.case_status:
        changed.append("case_status")

    if previous.notes != instance.notes:
        changed.append("notes")

    if not changed:
        return

    # Keep last_update in sync whenever these important fields change
    instance.last_update = timezone.now()

    # Fire the notification via the service helper
    notify_client_case_updated(instance, changed)
