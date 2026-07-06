from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

from core.models import Tenant
from core.tenancy import tenant_scope


class TenantMiddleware:
    """Resolves the tenant from the X-Tenant header or the request subdomain
    ({tenant}.sehaerp.sa) and runs the request inside a tenant scope:
    `request.tenant` set, transaction opened, `SET LOCAL app.tenant_id` applied
    so the RLS policies filter every query (docs/02 §2, docs/03 §3).

    No tenant resolved ⇒ request proceeds unscoped: the GUC stays unset and
    RLS returns zero rows for tenanted tables (fail closed).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.tenant = None

        exempt_prefixes = settings.TENANT_EXEMPT_PATHS
        if any(request.path.startswith(prefix) for prefix in exempt_prefixes):
            return self.get_response(request)

        subdomain = request.headers.get("X-Tenant") or self._subdomain_of(request)
        if not subdomain:
            return self.get_response(request)

        tenant = Tenant.objects.filter(subdomain=subdomain).first()
        if tenant is None:
            return JsonResponse(
                {
                    "code": "tenant.not_found",
                    "message_en": "Unknown clinic.",
                    "message_ar": "عيادة غير معروفة.",
                    "field_errors": {},
                },
                status=404,
            )

        request.tenant = tenant
        with tenant_scope(tenant.id):
            return self.get_response(request)

    @staticmethod
    def _subdomain_of(request: HttpRequest) -> str | None:
        host = request.get_host().split(":")[0]
        labels = host.split(".")
        # {tenant}.sehaerp.sa — anything shorter (localhost, bare domain) has no subdomain
        if len(labels) >= 3:
            return labels[0]
        return None
