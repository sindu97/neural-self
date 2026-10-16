"""API contract tests: envelopes, status codes, error codes and headers."""

import pytest

from neuralshelf.core.config import get_settings
from neuralshelf.main import app

pytestmark = pytest.mark.integration

API = "/api/v1"
PASSWORD = "CorrectHorse!42"

EXPECTED_PATHS = {
    "/api/v1/health/live",
    "/api/v1/health/ready",
    "/api/v1/auth/signup",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/revoke",
    "/api/v1/auth/me",
    "/api/v1/documents",
    "/api/v1/documents/{document_id}",
    "/api/v1/documents/{document_id}/reprocess",
    "/api/v1/retrieval/search",
    "/api/v1/conversations",
    "/api/v1/conversations/{conversation_id}",
    "/api/v1/conversations/{conversation_id}/messages",
    "/api/v1/conversations/{conversation_id}/messages/stream",
    "/api/v1/admin/ingestion-jobs",
    "/api/v1/admin/ingestion-jobs/stats",
    "/api/v1/admin/ingestion-jobs/retry-failed",
    "/api/v1/admin/ingestion-jobs/{job_id}/retry",
}


def assert_error(response, status_code: int, code: str) -> dict:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert body["success"] is False
    assert body["code"] == code
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["data"], list)
    return body


def signup(client, email: str = "dana@example.com"):
    return client.post(
        f"{API}/auth/signup", json={"name": "Dana", "email": email, "password": PASSWORD}
    )


def login(client, email: str = "dana@example.com", password: str = PASSWORD):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


def test_openapi_lists_every_public_endpoint(client) -> None:
    paths = set(client.get("/openapi.json").json()["paths"])
    assert EXPECTED_PATHS <= paths


def test_health_endpoints(client) -> None:
    live = client.get(f"{API}/health/live")
    assert live.status_code == 200
    assert live.json()["data"] == [{"status": "alive"}]

    ready = client.get(f"{API}/health/ready")
    assert ready.status_code == 200
    assert ready.json()["data"] == [{"database": "connected"}]


def test_unknown_route_and_wrong_method_use_error_envelope(client) -> None:
    assert_error(client.get(f"{API}/does-not-exist"), 404, "NOT_FOUND")
    assert_error(client.put(f"{API}/auth/login"), 405, "METHOD_NOT_ALLOWED")


def test_validation_errors_list_fields(client) -> None:
    body = assert_error(
        client.post(f"{API}/auth/signup", json={"name": "D", "email": "nope", "password": "x"}),
        422,
        "VALIDATION_ERROR",
    )
    assert {error["field"] for error in body["data"]} == {"name", "email", "password"}


def test_signup_returns_envelope_and_rejects_duplicates(client) -> None:
    response = signup(client)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    user = body["data"][0]
    assert user["email"] == "dana@example.com"
    assert user["is_admin"] is False
    assert "password_hash" not in user

    assert_error(signup(client), 409, "EMAIL_ALREADY_REGISTERED")


def test_login_and_me(client) -> None:
    signup(client)
    assert_error(login(client, password="WrongPassword!1"), 401, "INVALID_CREDENTIALS")

    tokens = login(client).json()["data"][0]
    assert tokens["token_type"] == "bearer"
    assert "refresh_token" not in tokens  # browsers get it as an httpOnly cookie
    assert tokens["user"]["is_admin"] is False

    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["data"][0]["email"] == "dana@example.com"


def test_missing_or_invalid_token_is_401_with_challenge(client) -> None:
    for headers in ({}, {"Authorization": "Bearer not-a-jwt"}):
        response = client.get(f"{API}/auth/me", headers=headers)
        assert_error(response, 401, "UNAUTHORIZED")
        assert response.headers["WWW-Authenticate"] == "Bearer"


TOKEN_MODE = {"X-Auth-Mode": "token"}


def test_refresh_token_reuse_revokes_every_session(client) -> None:
    signup(client)
    credentials = {"email": "dana@example.com", "password": PASSWORD}
    first = client.post(f"{API}/auth/login", json=credentials, headers=TOKEN_MODE)
    other = client.post(f"{API}/auth/login", json=credentials, headers=TOKEN_MODE)
    first_token = first.json()["data"][0]["refresh_token"]
    other_device = other.json()["data"][0]["refresh_token"]

    def refresh(token: str):
        return client.post(
            f"{API}/auth/refresh", json={"refresh_token": token}, headers=TOKEN_MODE
        )

    assert refresh(first_token).status_code == 200

    # Replaying the old token looks like theft: it fails and kills all sessions.
    assert_error(refresh(first_token), 401, "INVALID_REFRESH_TOKEN")
    assert_error(refresh(other_device), 401, "INVALID_REFRESH_TOKEN")


def test_revoke_is_idempotent_and_does_not_reveal_tokens(client) -> None:
    for _ in range(2):
        response = client.post(f"{API}/auth/revoke", json={"refresh_token": "unknown-token"})
        assert response.status_code == 200


def test_every_response_carries_a_request_id(client) -> None:
    generated = client.get(f"{API}/health/live").headers["X-Request-ID"]
    assert len(generated) == 32

    echoed = client.get(f"{API}/health/live", headers={"X-Request-ID": "gateway-abc.123"})
    assert echoed.headers["X-Request-ID"] == "gateway-abc.123"

    unsafe = client.get(f"{API}/health/live", headers={"X-Request-ID": "bad value\n"})
    assert unsafe.headers["X-Request-ID"] != "bad value\n"

    assert "X-Request-ID" in client.get(f"{API}/missing").headers


def test_cors_allows_configured_origins_only(client) -> None:
    allowed_origin = get_settings().cors_origins[0]
    preflight = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type",
    }

    allowed = client.options(
        f"{API}/auth/login", headers={"Origin": allowed_origin, **preflight}
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == allowed_origin

    blocked = client.options(
        f"{API}/auth/login", headers={"Origin": "https://evil.example", **preflight}
    )
    assert "access-control-allow-origin" not in blocked.headers


def test_login_is_rate_limited_per_email(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "rate_limit_login_per_email", 3)
    signup(client)

    for _ in range(3):
        login(client, password="WrongPassword!1")
    response = login(client)  # even the right password is refused now

    assert_error(response, 429, "RATE_LIMITED")
    assert 1 <= int(response.headers["Retry-After"]) <= get_settings().rate_limit_window_seconds
    # A different account from the same client is unaffected.
    signup(client, "erin@example.com")
    assert login(client, "erin@example.com").status_code == 200


def test_signup_is_rate_limited_per_ip(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "rate_limit_signup_per_ip", 2)

    assert signup(client, "a@example.com").status_code == 201
    assert signup(client, "b@example.com").status_code == 201
    assert_error(signup(client, "c@example.com"), 429, "RATE_LIMITED")


def test_app_metadata(client) -> None:
    assert app.title == "NeuralShelf"
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["data"][0]["docs"] == "/docs"
