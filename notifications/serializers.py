# notifications/serializers.py
from rest_framework import serializers
from cases.models import Case
from .models import AttorneyDevice, ClientDevice


class AttorneyDeviceRegisterSerializer(serializers.Serializer):
    # device_id == FCM token
    device_id = serializers.CharField(max_length=512)

    def create(self, validated_data):
        user = self.context["request"].user
        token = validated_data["device_id"]

        obj, _ = AttorneyDevice.objects.get_or_create(
            user=user,
            defaults={"device_ids": []},
        )

        devices = obj.device_ids or []
        if token not in devices:
            devices.append(token)
            obj.device_ids = devices
            obj.save(update_fields=["device_ids"])

        return obj


class ClientDeviceRegisterSerializer(serializers.Serializer):
    client_code = serializers.CharField(max_length=32)
    # device_id == FCM token
    device_id = serializers.CharField(max_length=512)

    def validate_client_code(self, value):
        from cases.models import Case  # keep or move to top as you prefer
        if not Case.objects.filter(client_code=value).exists():
            raise serializers.ValidationError("Invalid client code.")
        return value

    def create(self, validated_data):
        client_code = validated_data["client_code"]
        token = validated_data["device_id"]

        obj, _ = ClientDevice.objects.get_or_create(
            client_code=client_code,
            defaults={"device_ids": []},
        )

        devices = obj.device_ids or []
        if token not in devices:
            devices.append(token)
            obj.device_ids = devices
            obj.save(update_fields=["device_ids"])

        return obj
