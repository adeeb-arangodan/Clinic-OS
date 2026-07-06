import json

import pytest
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from core.middleware import TenantMiddleware
from core.tests.factories import TenantFactory

pytestmark = pytest.mark.django_db


def middleware_capturing(captured: dict) -> TenantMiddleware:
    def view(request: HttpRequest) -> HttpResponse:
        captured["tenant"] = request.tenant
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.tenant_id', true)")
            captured["guc"] = cursor.fetchone()[0]
        return HttpResponse("ok")

    return TenantMiddleware(view)


def test_resolves_tenant_from_x_tenant_header() -> None:
    tenant = TenantFactory(subdomain="alpha")
    captured: dict = {}

    request = RequestFactory().get("/api/v1/anything/", headers={"X-Tenant": "alpha"})
    response = middleware_capturing(captured)(request)

    assert response.status_code == 200
    assert captured["tenant"] == tenant
    assert captured["guc"] == str(tenant.id)


def test_resolves_tenant_from_subdomain() -> None:
    tenant = TenantFactory(subdomain="beta")
    captured: dict = {}

    request = RequestFactory().get("/api/v1/anything/", HTTP_HOST="beta.sehaerp.sa")
    response = middleware_capturing(captured)(request)

    assert response.status_code == 200
    assert captured["tenant"] == tenant


def test_unknown_tenant_returns_error_envelope() -> None:
    request = RequestFactory().get("/api/v1/anything/", headers={"X-Tenant": "ghost"})
    response = TenantMiddleware(lambda r: HttpResponse("ok"))(request)

    assert response.status_code == 404
    body = json.loads(response.content)
    assert body["code"] == "tenant.not_found"
    assert body["message_en"] and body["message_ar"]


def test_no_subdomain_or_header_proceeds_unscoped() -> None:
    captured: dict = {}

    request = RequestFactory().get("/api/v1/anything/", HTTP_HOST="localhost")
    response = middleware_capturing(captured)(request)

    assert response.status_code == 200
    assert captured["tenant"] is None
    assert captured["guc"] in (None, "")


def test_exempt_path_skips_resolution() -> None:
    TenantFactory(subdomain="gamma")
    captured: dict = {}

    request = RequestFactory().get("/api/v1/health/", headers={"X-Tenant": "gamma"})
    response = middleware_capturing(captured)(request)

    assert response.status_code == 200
    assert captured["tenant"] is None
