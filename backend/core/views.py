import uuid

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core import selectors, services
from core.serializers import LoginSerializer, SessionSerializer

REFRESH_COOKIE_PATH = "/api/v1/auth/"


def _set_refresh_cookie(response: Response, refresh: str) -> None:
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE,
        refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite="Lax",
        path=REFRESH_COOKIE_PATH,
    )


def _token_response(pair: services.TokenPair, http_status: int = status.HTTP_200_OK) -> Response:
    user = pair.user
    response = Response(
        {
            "access": pair.access,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "tenant": user.tenant.subdomain if user.tenant_id else None,
                "permissions": sorted(selectors.permission_codes_for_user(user)),
            },
        },
        status=http_status,
    )
    _set_refresh_cookie(response, pair.refresh)
    return response


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses=OpenApiResponse(description="Service is up"))
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class LoginView(APIView):
    """POST /auth/login/ — access token in body, rotating refresh in an
    httpOnly cookie (PLT-6, docs/02 §7)."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(request=LoginSerializer, responses=OpenApiResponse(description="Token pair"))
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pair = services.login(
            request=request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
            user_agent=request.headers.get("User-Agent", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return _token_response(pair)


class RefreshView(APIView):
    """POST /auth/refresh/ — rotates the cookie refresh token, returns a new access."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(request=None, responses=OpenApiResponse(description="New token pair"))
    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE, "")
        pair = services.refresh_session(request=request, raw_refresh=raw)
        return _token_response(pair)


class LogoutView(APIView):
    """POST /auth/logout/ — blacklists the refresh token, clears the cookie."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(request=None, responses=OpenApiResponse(description="Logged out"))
    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE, "")
        if raw:
            services.logout(raw_refresh=raw)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.JWT_REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)
        return response


class SessionListView(APIView):
    """GET /auth/sessions/ — the caller's active devices (PLT-6)."""

    @extend_schema(responses=SessionSerializer(many=True))
    def get(self, request: Request) -> Response:
        sessions = selectors.active_sessions_for_user(request.user)
        current_sid = request.auth.get("sid") if request.auth else None
        serializer = SessionSerializer(sessions, many=True, context={"current_sid": current_sid})
        return Response({"results": serializer.data})


class SessionRevokeView(APIView):
    """POST /auth/sessions/{id}/revoke/ — state transition as POST sub-action (rule 10)."""

    @extend_schema(request=None, responses=OpenApiResponse(description="Session revoked"))
    def post(self, request: Request, session_id: uuid.UUID) -> Response:
        services.revoke_session(user=request.user, session_id=session_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
