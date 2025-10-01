import logging
from typing import Any, Mapping, Tuple, Optional

from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import ErrorDetail

logger = logging.getLogger(__name__)


def _first_message_and_code(payload: Any) -> Tuple[str, Optional[str]]:
    """
    Extract a single human-friendly message (and optional code) from common DRF shapes:
      - {"non_field_errors": ["..."]} or {"field": ["..."]}
      - {"field": "..."}
      - ["..."]
      - ErrorDetail(...)
      - "..."
    """
    # ErrorDetail instance
    if isinstance(payload, ErrorDetail):
        return str(payload), getattr(payload, "code", None)

    # Mapping (dict-like)
    if isinstance(payload, Mapping):
        # Prefer non_field_errors
        nfe = payload.get("non_field_errors")
        if isinstance(nfe, list) and nfe:
            msg, code = _first_message_and_code(nfe[0])
            return msg, code
        # Otherwise first field error/message
        for v in payload.values():
            msg, code = _first_message_and_code(v)
            if msg:
                return msg, code
        return "Request could not be processed.", None

    # List/tuple: take first item
    if isinstance(payload, (list, tuple)) and payload:
        return _first_message_and_code(payload[0])

    # Plain string
    if isinstance(payload, str):
        return payload, None

    return "Request could not be processed.", None


def custom_exception_handler(exc, context):
    """
    Wrap DRF responses into:
      {
        "error": {
          "message": "...one clean line...",
          "code": "...optional...",
          "details": <original DRF payload>
        }
      }
    """
    # Let DRF build base response (status + default data)
    response = drf_exception_handler(exc, context)

    # Django ValidationError -> force our envelope
    if isinstance(exc, ValidationError):
        details = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
        msg, code = _first_message_and_code(details)
        return Response(
            {"error": {"message": msg, "code": code or "VALIDATION_ERROR", "details": details}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if response is not None:
        original = response.data if isinstance(response.data, dict) else {}
        # Prefer clean extraction from DRF payload over str(exc)
        msg, code = _first_message_and_code(original if original else str(exc))

        response.data = {
            "error": {
                "message": msg,
                "code": code or getattr(exc, "code", "ERROR"),
                "details": original,
            }
        }

        view = context.get("view")
        view_name = getattr(view, "__class__", type("X", (), {})).__name__
        logger.error("API Error: %s - Context: %s", exc, view_name)

    return response
