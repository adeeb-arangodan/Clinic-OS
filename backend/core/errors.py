"""API error envelope per docs/03 §3: every error body is
`{code, message_en, message_ar, field_errors}` (CLAUDE.md rule 10).

Raise ApiError("some.code", status) from services; DRF's own exceptions
(validation, auth, permission) are translated by `api_exception_handler`,
which resolves bilingual messages from CATALOG by error code (rule 8: no
user-facing string ships without both en and ar).
"""

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

# code → (message_en, message_ar)
CATALOG: dict[str, tuple[str, str]] = {
    "auth.invalid_credentials": (
        "Invalid username or password.",
        "اسم المستخدم أو كلمة المرور غير صحيحة.",
    ),
    "auth.token_invalid": (
        "Your session has expired or is invalid. Please sign in again.",
        "انتهت جلستك أو أنها غير صالحة. الرجاء تسجيل الدخول مرة أخرى.",
    ),
    "auth.not_authenticated": (
        "Authentication required.",
        "المصادقة مطلوبة.",
    ),
    "auth.permission_denied": (
        "You do not have permission to perform this action.",
        "ليس لديك صلاحية لتنفيذ هذا الإجراء.",
    ),
    "entitlement.not_enabled": (
        "This feature is not enabled for your clinic.",
        "هذه الميزة غير مفعّلة لعيادتكم.",
    ),
    "session.not_found": (
        "Session not found.",
        "الجلسة غير موجودة.",
    ),
    "tenant.not_found": (
        "Unknown clinic.",
        "عيادة غير معروفة.",
    ),
    "validation.invalid": (
        "Some fields are invalid.",
        "بعض الحقول غير صالحة.",
    ),
    "error.internal": (
        "Something went wrong. Please try again.",
        "حدث خطأ ما. الرجاء المحاولة مرة أخرى.",
    ),
}

# DRF built-in exception codes → our envelope codes
_DRF_CODE_MAP = {
    "authentication_failed": "auth.invalid_credentials",
    "not_authenticated": "auth.not_authenticated",
    "token_not_valid": "auth.token_invalid",
    "permission_denied": "auth.permission_denied",
    "invalid": "validation.invalid",
}


def envelope(code: str, field_errors: dict[str, Any] | None = None) -> dict[str, Any]:
    message_en, message_ar = CATALOG.get(code, CATALOG["error.internal"])
    return {
        "code": code,
        "message_en": message_en,
        "message_ar": message_ar,
        "field_errors": field_errors or {},
    }


class ApiError(APIException):
    """Service-layer error carrying an envelope code from CATALOG."""

    def __init__(
        self,
        code: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        field_errors: dict[str, Any] | None = None,
    ) -> None:
        self.envelope_code = code
        self.status_code = status_code
        self.field_errors = field_errors or {}
        super().__init__(detail=CATALOG.get(code, CATALOG["error.internal"])[0], code=code)


def _flatten_code(codes: Any) -> str:
    """exc.get_codes() returns str | list | dict depending on the exception."""
    while isinstance(codes, dict):
        codes = next(iter(codes.values()), "invalid")
    if isinstance(codes, list):
        codes = codes[0] if codes else "invalid"
    return str(codes)


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ApiError):
        response.data = envelope(exc.envelope_code, exc.field_errors)
        return response

    if isinstance(exc, ValidationError):
        detail = exc.detail if isinstance(exc.detail, dict) else {"non_field_errors": exc.detail}
        field_errors = {field: [str(e) for e in errors] for field, errors in detail.items()}
        response.data = envelope("validation.invalid", field_errors)
        return response

    if isinstance(exc, APIException):
        drf_code = _flatten_code(exc.get_codes())
        code = _DRF_CODE_MAP.get(drf_code, drf_code if drf_code in CATALOG else "error.internal")
        response.data = envelope(code)
        return response

    return response
