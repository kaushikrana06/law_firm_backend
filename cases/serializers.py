from rest_framework import serializers
from .models import Case

class CasePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = (
            "id",
            "firm_name", 
            "firm_email", 
            "firm_phone",
            "case_type",
            "case_status",
            "date_opened",
            "last_update",
            "notes",
        )

class ClientPublicSerializer(serializers.Serializer):
    # Not a ModelSerializer anymore — we synthesize this from Case rows
    name = serializers.CharField()
    code = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    cases = CasePublicSerializer(many=True)

class AttorneyItemSerializer(serializers.ModelSerializer):
    case_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Case
        fields = (
            "case_id",
            "client_name", "client_code", "client_email", "client_phone",
            "firm_name", "firm_email", "firm_phone",
            "case_type", "case_status",
            "date_opened", "last_update",
            "notes",
        )

class CaseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = ("notes", "case_status")
