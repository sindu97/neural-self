"""Browser auth: refresh token in an httpOnly cookie, CSRF header, logout."""

import pytest
from fastapi import Response

from neuralshelf.core.config import get_settings
from neuralshelf.features.auth.cookies import set_refresh_cookie

pytestmark = pytest.mark.integration

API = "/api/v1"
CREDENTIALS = {"email": "web@example.com", "password": "CorrectHorse!42"}
CSRF = {"X-NeuralShelf-CSRF": "1"}


@pytest.fixture
def web_login(client):
    client.post(f"{API}/auth/signup", json={"name": "Web User", **CREDENTIALS})
    return client.post(f"{API}/auth/login", json=CREDENTIALS)


def refresh_cookie(response) -> str:
    return next(
        header
        for header in response.headers.get_list("set-cookie")
        if header.startswith(f"{get_settings().auth_cookie_name}=")
    )


def test_login_sets_httponly_cookie_and_keeps_token_out_of_body(web_login) -> None:
    assert web_login.status_code == 200
    body = web_login.json()["data"][0]
    assert "refresh_token" not in body
    assert body["access_token"] and body["user"]["email"] == CREDENTIALS["email"]

    cookie = refresh_cookie(web_login).lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api/v1/auth" in cookie
    assert "max-age=604800" in cookie  # 7 days


def test_refresh_with_cookie_rotates_it_and_returns_the_user(client, web_login) -> None:
    old_cookie = client.cookies.get(get_settings().auth_cookie_name)

    response = client.post(f"{API}/auth/refresh", headers=CSRF)

    assert response.status_code == 200
    body = response.json()["data"][0]
    assert body["access_token"]
    assert body["user"]["email"] == CREDENTIALS["email"]
    assert "refresh_token" not in body
    assert client.cookies.get(get_settings().auth_cookie_name) != old_cookie


def test_cookie_refresh_without_csrf_header_is_rejected(client, web_login) -> None:
    response = client.post(f"{API}/auth/refresh")

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_CHECK_FAILED"


def test_refresh_without_cookie_or_body_is_401(client) -> None:
    response = client.post(f"{API}/auth/refresh", headers=CSRF)

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_REFRESH_TOKEN"


def test_logout_revokes_and_clears_the_cookie(client, web_login) -> None:
    stolen_copy = client.cookies.get(get_settings().auth_cookie_name)

    response = client.post(f"{API}/auth/revoke", headers=CSRF)

    assert response.status_code == 200
    assert "max-age=0" in refresh_cookie(response).lower()
    assert client.cookies.get(get_settings().auth_cookie_name) is None
    # Even a copy of the old cookie no longer works.
    client.cookies.set(get_settings().auth_cookie_name, stolen_copy, path="/api/v1/auth")
    assert client.post(f"{API}/auth/refresh", headers=CSRF).status_code == 401


def test_native_token_mode_uses_the_body_and_sets_no_cookie(client) -> None:
    client.post(f"{API}/auth/signup", json={"name": "App User", **CREDENTIALS})

    response = client.post(
        f"{API}/auth/login", json=CREDENTIALS, headers={"X-Auth-Mode": "token"}
    )

    assert response.json()["data"][0]["refresh_token"]
    assert not response.headers.get_list("set-cookie")


def test_cookie_is_secure_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "auth_cookie_secure", True)
    response = Response()

    set_refresh_cookie(response, "token-value")

    assert "secure" in response.headers["set-cookie"].lower()


def test_cookie_is_secure_by_default_in_production(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_cookie_secure", None)
    monkeypatch.setattr(settings, "app_env", "production")

    assert settings.refresh_cookie_secure is True
