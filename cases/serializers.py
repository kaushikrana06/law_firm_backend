from rest_framework import serializers
from .models import Client, Case


class CasePublicSerializer(serializers.ModelSerializer):
    firm_name = serializers.CharField(source="firm.name", read_only=True)

    class Meta:
        model = Case
        fields = (
            "id",
            "firm_name",
            "case_type",
            "case_status",
            "date_opened",
            "last_update",
            "notes",
        )


class ClientPublicSerializer(serializers.ModelSerializer):
    cases = CasePublicSerializer(many=True, read_only=True)

    class Meta:
        model = Client
        fields = ("name", "code", "email", "phone", "cases")



class AttorneyItemSerializer(serializers.ModelSerializer):
    case_id = serializers.UUIDField(source="id", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    client_code = serializers.CharField(source="client.code", read_only=True)
    client_email = serializers.EmailField(source="client.email", read_only=True)
    client_phone = serializers.CharField(source="client.phone", read_only=True)
    firm_name = serializers.CharField(source="firm.name", read_only=True)

    class Meta:
        model = Case
        fields = (
            "case_id",
            "client_name", "client_code", "client_email", "client_phone",
            "firm_name",
            "case_type", "case_status",
            "date_opened", "last_update",
            "notes",
        )


class CaseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = ("notes", "case_status")
