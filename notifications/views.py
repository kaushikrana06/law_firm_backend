# notifications/views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import AttorneyDevice, ClientDevice


class AttorneyDeviceRegisterView(APIView):
    """
    POST /api/notifications/attorney/device/
    Body: { "device_id": "<fcm_token>" }

    Appends the token into AttorneyDevice.device_ids (single row per user).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        device_id = (request.data.get("device_id") or "").strip()
        if not device_id:
            return Response(
                {"detail": "device_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj, _ = AttorneyDevice.objects.get_or_create(
            user=request.user,
            defaults={"device_ids": []},
        )

        devices = obj.device_ids or []
        if device_id not in devices:
            devices.append(device_id)
            obj.device_ids = devices
            obj.save(update_fields=["device_ids"])

        return Response({"detail": "OK"}, status=status.HTTP_200_OK)


class ClientDeviceRegisterView(APIView):
    """
    POST /api/notifications/client/device/
    Body: { "client_code": "<code>", "device_id": "<fcm_token>" }

    Appends the token into ClientDevice.device_ids (single row per client_code).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        client_code = (request.data.get("client_code") or "").strip()
        device_id = (request.data.get("device_id") or "").strip()

        if not client_code or not device_id:
            return Response(
                {"detail": "client_code and device_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj, _ = ClientDevice.objects.get_or_create(
            client_code=client_code,
            defaults={"device_ids": []},
        )

        devices = obj.device_ids or []
        if device_id not in devices:
            devices.append(device_id)
            obj.device_ids = devices
            obj.save(update_fields=["device_ids"])

        return Response({"detail": "OK"}, status=status.HTTP_200_OK)
