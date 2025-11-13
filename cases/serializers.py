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
    status_note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Case
        fields = ("notes", "case_status", "status_note")
        # make notes & case_status optional so partial payloads work
        extra_kwargs = {
            "notes": {"required": False},
            "case_status": {"required": False},
        }

    def update(self, instance, validated_data):
        # remember previous status
        old_status = instance.case_status

        # None means "field not sent at all"
        status_note_text = validated_data.pop("status_note", None)

        # update the Case itself (notes / case_status)
        instance = super().update(instance, validated_data)

        # figure out who is editing (may be None)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user is not None and not getattr(user, "is_authenticated", False):
            user = None

        # CASE 1 & 3: client SENT status_note (even empty string)
        if status_note_text is not None:
            instance.add_status_note(
                status_note_text,
                status=instance.case_status,
                created_by=user,
            )

        # CASE 2: status changed but no status_note field sent
        elif instance.case_status != old_status:
            # create/update note with empty text for the new status
            instance.add_status_note(
                "",
                status=instance.case_status,
                created_by=user,
            )

        return instance

    def to_representation(self, instance):
        """
        Always return:
        {
          "notes": ...,
          "case_status": ...,
          "status_note": <latest note text for current status or "">
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

