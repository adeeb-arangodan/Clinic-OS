from rest_framework import serializers

from core.models import AuditLog, AuthSession


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()  # username or email (PLT-6)
    password = serializers.CharField(trim_whitespace=False)


class UserSummarySerializer(serializers.Serializer):
    """Login/refresh payload consumed by the frontend auth + feature-flag
    contexts (rule 9). Response documentation only — built in the view."""

    id = serializers.UUIDField()
    username = serializers.CharField()
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)
    tenant = serializers.CharField(allow_null=True)
    permissions = serializers.ListField(child=serializers.CharField())
    features = serializers.ListField(child=serializers.CharField())


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    user = UserSummarySerializer()


class SessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = AuthSession
        fields = ["id", "user_agent", "ip_address", "created_at", "last_refreshed_at", "is_current"]

    def get_is_current(self, session: AuthSession) -> bool:
        return str(session.id) == self.context.get("current_sid")


class SessionListSerializer(serializers.Serializer):
    results = SessionSerializer(many=True)


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


class PaginatedAuditLogSerializer(serializers.Serializer):
    """Response documentation for the cursor-paginated audit list (docs/03 §3)."""

    results = AuditLogSerializer(many=True)
    next = serializers.URLField(allow_null=True)
    prev = serializers.URLField(allow_null=True)
