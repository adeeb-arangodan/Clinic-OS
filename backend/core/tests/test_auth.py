"""PLT-6: login (username/email), refresh rotation, logout, session list/revoke.

Uses the Django test client end-to-end so TenantMiddleware, the exception
handler and cookies are all exercised.
"""

import pytest
from django.conf import settings
from django.test import Client
from rest_framework_simplejwt.tokens import AccessToken

from core.tests.factories import TenantFactory, UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "correct-horse-9!"


def login(client: Client, subdomain: str, username: str, password: str = PASSWORD):
    return client.post(
        "/api/v1/auth/login/",
        {"username": username, "password": password},
        content_type="application/json",
        headers={"X-Tenant": subdomain},
    )


@pytest.fixture
def tenant():
    return TenantFactory(subdomain="alpha")


@pytest.fixture
def user(tenant):
    return UserFactory(tenant=tenant, username="reception1", email="reception1@clinic.sa")


def test_login_returns_access_token_and_refresh_cookie(client, tenant, user) -> None:
    response = login(client, "alpha", "reception1")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["username"] == "reception1"
    assert body["user"]["tenant"] == "alpha"

    claims = AccessToken(body["access"])
    assert claims["tenant"] == "alpha"
    assert claims["sid"]

    cookie = response.cookies[settings.JWT_REFRESH_COOKIE]
    assert cookie["httponly"]
    assert cookie["path"] == "/api/v1/auth/"


def test_login_accepts_email(client, tenant, user) -> None:
    response = login(client, "alpha", "reception1@clinic.sa")
    assert response.status_code == 200


def test_login_wrong_password_returns_envelope(client, tenant, user) -> None:
    response = login(client, "alpha", "reception1", password="wrong")

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "auth.invalid_credentials"
    assert body["message_en"] and body["message_ar"]
    assert settings.JWT_REFRESH_COOKIE not in response.cookies


def test_login_on_other_tenant_rejected_like_bad_credentials(client, tenant, user) -> None:
    TenantFactory(subdomain="beta")
    response = login(client, "beta", "reception1")

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_credentials"


def test_refresh_rotates_token_and_blacklists_old_one(client, tenant, user) -> None:
    old_refresh = login(client, "alpha", "reception1").cookies[settings.JWT_REFRESH_COOKIE].value

    first = client.post("/api/v1/auth/refresh/", headers={"X-Tenant": "alpha"})
    assert first.status_code == 200
    assert first.json()["access"]
    new_refresh = first.cookies[settings.JWT_REFRESH_COOKIE].value
    assert new_refresh != old_refresh

    # replaying the pre-rotation token must fail (it is blacklisted)
    client.cookies[settings.JWT_REFRESH_COOKIE] = old_refresh
    replay = client.post("/api/v1/auth/refresh/", headers={"X-Tenant": "alpha"})
    assert replay.status_code == 401
    assert replay.json()["code"] == "auth.token_invalid"


def test_logout_clears_cookie_and_kills_session(client, tenant, user) -> None:
    login(client, "alpha", "reception1")
    refresh = client.cookies[settings.JWT_REFRESH_COOKIE].value

    response = client.post("/api/v1/auth/logout/", headers={"X-Tenant": "alpha"})
    assert response.status_code == 204
    assert response.cookies[settings.JWT_REFRESH_COOKIE].value == ""

    client.cookies[settings.JWT_REFRESH_COOKIE] = refresh
    after = client.post("/api/v1/auth/refresh/", headers={"X-Tenant": "alpha"})
    assert after.status_code == 401


def test_session_list_shows_devices_and_revoke_disables_refresh(tenant, user) -> None:
    desk = Client()
    phone = Client()
    access = login(desk, "alpha", "reception1").json()["access"]
    login(phone, "alpha", "reception1")

    listing = desk.get(
        "/api/v1/auth/sessions/",
        headers={"X-Tenant": "alpha", "Authorization": f"Bearer {access}"},
    )
    assert listing.status_code == 200
    sessions = listing.json()["results"]
    assert len(sessions) == 2
    current = [s for s in sessions if s["is_current"]]
    other = [s for s in sessions if not s["is_current"]]
    assert len(current) == 1 and len(other) == 1

    revoke = desk.post(
        f"/api/v1/auth/sessions/{other[0]['id']}/revoke/",
        headers={"X-Tenant": "alpha", "Authorization": f"Bearer {access}"},
    )
    assert revoke.status_code == 204

    refreshed = phone.post("/api/v1/auth/refresh/", headers={"X-Tenant": "alpha"})
    assert refreshed.status_code == 401


def test_sessions_require_authentication(client, tenant) -> None:
    response = client.get("/api/v1/auth/sessions/", headers={"X-Tenant": "alpha"})
    assert response.status_code == 401
    assert response.json()["code"] == "auth.not_authenticated"
