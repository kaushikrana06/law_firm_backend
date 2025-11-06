# notifications/models.py
from django.conf import settings
from django.db import models


class AttorneyDevice(models.Model):
    """
    One row per attorney.
    device_ids is a JSON list of FCM registration tokens for that attorney's devices.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attorney_devices",
    )
    # List of FCM registration tokens
    device_ids = models.JSONField(default=list, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        ids = self.device_ids or []
        if not ids:
            return f"{self.user_id} - <no devices>"
        return f"{self.user_id} - {len(ids)} device(s)"


class ClientDevice(models.Model):
    """
    One row per client_code.
    device_ids is a JSON list of FCM registration tokens for that client.
    """

    client_code = models.CharField(max_length=32, unique=True, db_index=True)
    device_ids = models.JSONField(default=list, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["client_code"]),
        ]

    def __str__(self) -> str:
        ids = self.device_ids or []
        if not ids:
            return f"{self.client_code} - <no devices>"
        return f"{self.client_code} - {len(ids)} device(s)"
