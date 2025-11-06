from typing import Iterable, Sequence, Optional, Dict
import logging

from django.conf import settings

import firebase_admin
from firebase_admin import credentials, messaging

from .models import AttorneyDevice, ClientDevice

logger = logging.getLogger(__name__)


if not firebase_admin._apps:
    if getattr(settings, "FIREBASE_CREDENTIALS_FILE", None):
        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_FILE)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase app initialized for FCM.")
        except Exception:
            logger.exception("Failed to initialize Firebase app")
    else:
        logger.warning(
            "FIREBASE_CREDENTIALS_FILE not configured; Firebase not initialized."
        )


class FcmNotification:
    def __init__(
        self,
        device_ids: Sequence[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> None:
        self.device_ids = [t for t in device_ids if t]
        self.title = title
        self.body = body
        self.data: Dict[str, str] = {
            str(k): str(v) for k, v in (data or {}).items()
        }

    def run(self) -> int:
        if not self.device_ids:
            return 0

        if not firebase_admin._apps:
            logger.warning(
                "Firebase app not initialized; skipping push notification."
            )
            return 0

        success_count = 0
        for token in self.device_ids:
            message = messaging.Message(
                token=token,
                notification=messaging.Notification(
                    title=self.title,
                    body=self.body,
                ),
                data=self.data,
            )
            try:
                messaging.send(message)
                success_count += 1
            except Exception:
                logger.exception("Error sending FCM push to token=%s", token)

        logger.info(
            "FCM push finished: attempted=%s, success=%s",
            len(self.device_ids),
            success_count,
        )
        return success_count


def notify_client_case_updated(case, changed_fields: Iterable[str]) -> int:
    changed_fields_set = set(changed_fields)
    title = "Your case was updated"

    details = []
    if "case_status" in changed_fields_set:
        details.append(f"Status → {case.case_status}")
    if "notes" in changed_fields_set:
        details.append("New note added")

    body = "; ".join(details) or "Your case details have changed."

    try:
        record = ClientDevice.objects.get(client_code=case.client_code)
        device_ids = record.device_ids or []
    except ClientDevice.DoesNotExist:
        device_ids = []

    notification = FcmNotification(
        device_ids=device_ids,
        title=title,
        body=body,
        data={
            "type": "case_update",
            "case_id": str(case.id),
            "client_code": case.client_code,
        },
    )
    return notification.run()


def notify_attorney_call_request(case) -> int:
    if not getattr(case, "attorney_id", None):
        logger.info(
            "Case %s has no attorney; skipping call-request notification.", case.id
        )
        return 0

    title = "Client requested a call"
    body = f"{case.client_name} ({case.client_code}) asked you to call them."

    try:
        record = AttorneyDevice.objects.get(user_id=case.attorney_id)
        device_ids = record.device_ids or []
    except AttorneyDevice.DoesNotExist:
        device_ids = []

    notification = FcmNotification(
        device_ids=device_ids,
        title=title,
        body=body,
        data={
            "type": "call_request",
            "case_id": str(case.id),
            "client_code": case.client_code,
        },
    )
    return notification.run()