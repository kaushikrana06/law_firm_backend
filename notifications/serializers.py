# notifications/serializers.py
from rest_framework import serializers

from cases.models import Case
from .models import AttorneyDevice, ClientDevice


class AttorneyDeviceRegisterSerializer(serializers.Serializer):
    # device_id == FCM token
    device_id = serializers.CharField(max_length=512)

    def create(self, validated_data):
        user = self.context["request"].user

        obj, _ = AttorneyDevice.objects.update_or_create(
            user=user,
            device_id=validated_data["device_id"],
        )
        return obj


class ClientDeviceRegisterSerializer(serializers.Serializer):
    client_code = serializers.CharField(max_length=32)
    # device_id == FCM token
    device_id = serializers.CharField(max_length=512)

    def validate_client_code(self, value):
        if not Case.objects.filter(client_code=value).exists():
            raise serializers.ValidationError("Invalid client code.")
        return value

    def create(self, validated_data):
        obj, _ = ClientDevice.objects.update_or_create(
            client_code=validated_data["client_code"],
            device_id=validated_data["device_id"],
        )
        return obj
