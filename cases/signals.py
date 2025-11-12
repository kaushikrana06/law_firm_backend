# cases/signals.py
from typing import List

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Case, CaseNote
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

@receiver(post_save, sender=CaseNote)
def case_status_note_changed(sender, instance: CaseNote, created: bool, **kwargs) -> None:
    """
    Whenever a status_note (CaseNote) is created or updated,
    send a 'notes' change notification to the client.
    """
    case = instance.case

    # If for some reason there's no client_code, nothing to notify
    if not case.client_code:
        return

    # Optionally bump last_update on the Case
    case.last_update = timezone.now()
    case.save(update_fields=["last_update"])

    # Re-use the existing 'notes' semantics in notify_client_case_updated
    notify_client_case_updated(case, changed_fields=["notes"])