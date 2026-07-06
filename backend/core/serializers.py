from rest_framework import serializers

from core.models import AuthSession


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
