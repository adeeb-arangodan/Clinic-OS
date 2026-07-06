from rest_framework import serializers

from core.models import AuditLog, AuthSession


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()  # username or email (PLT-6)
    password = serializers.CharField(trim_whitespace=False)


class SessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = AuthSession
        fields = ["id", "user_agent", "ip_address", "created_at", "last_refreshed_at", "is_current"]

    def get_is_current(self, session: AuthSession) -> bool:
        return str(session.id) == self.context.get("current_sid")


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", default=None, read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "created_at",
            "actor_id",
            "actor_username",
            "branch_id",
            "action",
            "entity_type",
            "entity_id",
            "before",
            "after",
            "ip",
            "request_id",
        ]
        read_only_fields = fields
