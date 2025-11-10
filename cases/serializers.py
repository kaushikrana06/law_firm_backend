from rest_framework import serializers
from .models import Case, CaseNote

class CaseNoteSerializer(serializers.ModelSerializer):
    case_status = serializers.CharField(source="status")
    class Meta:
        model = CaseNote
        fields = ("id", "case_status", "status_note", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class CasePublicSerializer(serializers.ModelSerializer):
    status_notes = CaseNoteSerializer(many=True, read_only=True)
    class Meta:
        model = Case
        fields = (
            "id",
            "firm_name", 
            "firm_email", 
            "firm_phone",
            "case_type",
            "date_opened",
            "last_update",
            "notes",
            "status_notes",
        )

class ClientPublicSerializer(serializers.Serializer):
    name = serializers.CharField()
    code = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    cases = CasePublicSerializer(many=True)

class AttorneyItemSerializer(serializers.ModelSerializer):
    case_id = serializers.UUIDField(source="id", read_only=True)
    status_notes = CaseNoteSerializer(many=True, read_only=True)
    class Meta:
        model = Case
        fields = (
            "case_id",
            "client_name", "client_code", "client_email", "client_phone",
            "firm_name", "firm_email", "firm_phone",
            "case_type",
            "date_opened", "last_update",
            "notes",
            "status_notes",
        )

class CaseUpdateSerializer(serializers.ModelSerializer):
    # extra field in the API, not a model field on Case
    status_note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Case
        fields = ("notes", "case_status", "status_note")

    def update(self, instance, validated_data):
        # Pull out status_note text (not a Case field)
        status_note_text = (validated_data.pop("status_note", "") or "").strip()

        # Update Case.notes and/or Case.case_status
        instance = super().update(instance, validated_data)

        # If a status_note was sent, update the note for the current status
        if status_note_text:
            request = self.context.get("request")
            user = None
            if request is not None and getattr(request, "user", None) and request.user.is_authenticated:
                user = request.user

            # add_status_note does "update or create" for this status
            instance.add_status_note(
                status_note_text,
                status=instance.case_status,
                created_by=user,
            )

        return instance

    def to_representation(self, instance):
        """
        After saving, return exactly:
        {
          "notes": ...,
          "case_status": ...,
          "status_note": <latest note for the current status>
        }
        """
        rep = super().to_representation(instance)

        latest = (
            instance.status_notes
            .filter(status=instance.case_status)
            .order_by("-created_at")
            .first()
        )
        rep["status_note"] = latest.status_note if latest else ""

        return rep

