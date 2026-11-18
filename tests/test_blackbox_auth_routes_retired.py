"""Blackbox frontdoor tests: gateway token minting, admin seeding, and mail routes are retired (TASK-0523).

Governing ADRs: ADR-0005 (Zitadel is the only token issuer), ADR-0015 (audit remediation: Zitadel
issues all tokens and no role name grants access).
Verifies through public HTTP and the OpenAPI document only:
1. Every retired route returns 404 or 405.
2. The OpenAPI document lists no retired auth path.
3. Credentials sent to any remaining route cannot obtain a token.
4. The old dev-signed token (literal signature) is refused by the profile route.

The `/api/v1/auth/sync/*` routes belong to TASK-0543 and are excluded from the path check.
"""

import jwt
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app

client = TestClient(app)

RETIRED_ROUTES = [
    ("POST", "/api/v1/auth/token"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/verify"),
    ("POST", "/api/v1/auth/verify-email"),
    ("POST", "/api/v1/auth/resend-verification"),
    ("POST", "/api/v1/auth/admin/seed"),
    ("POST", "/api/v1/auth/admin/invite"),
    ("POST", "/api/v1/auth/dev/send-test"),
    ("POST", "/api/v1/auth/test-email"),
    ("GET", "/api/v1/auth/dev/emails"),
    ("DELETE", "/api/v1/auth/dev/emails"),
    ("GET", "/api/v1/auth/dev/stats"),
    ("GET", "/api/v1/auth/mailpit/status"),
]

RETIRED_PATHS = {path for _, path in RETIRED_ROUTES}

ARBITRARY_CREDENTIALS = {
    "username": "evelyn-dm",
    "password": "anything-at-all",
    "email": "evelyn@runefoble.local",
    "to": "evelyn@runefoble.local",
    "grant_type": "password",
}


@pytest.mark.parametrize(("method", "path"), RETIRED_ROUTES)
def test_retired_route_is_not_served(method: str, path: str) -> None:
    """A retired route answers 404 or 405 for any caller, even with credentials."""
    res = client.request(method, path, json=ARBITRARY_CREDENTIALS)
    assert res.status_code in (404, 405), f"{method} {path} returned {res.status_code}"
    assert "access_token" not in res.text


def test_openapi_lists_no_retired_auth_path() -> None:
    """The published OpenAPI document contains no retired path and no auth path except sync."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    paths = res.json()["paths"]

    assert RETIRED_PATHS.isdisjoint(paths.keys())
    auth_paths = [
        p for p in paths if p.startswith("/api/v1/auth") and not p.startswith("/api/v1/auth/sync/")
    ]
    assert auth_paths == []


def test_password_grant_cannot_obtain_a_token() -> None:
    """Any username and password pair yields no access token from the gateway."""
    for username in ("evelyn-dm", "dungeon-master", "anyone"):
        res = client.post(
            "/api/v1/auth/token",
            data={"username": username, "password": "anything", "grant_type": "password"},
        )
        assert res.status_code in (404, 405)
        assert "access_token" not in res.text


def test_dev_signed_token_is_refused_by_profile(signing_issuer) -> None:
    """A token signed with the retired literal secret fails verification on the profile route."""
    legacy_token = jwt.encode(
        {"sub": "user-evelyn-dm", "preferred_username": "evelyn-dm", "roles": ["dm", "player"]},
        "runefoble-dev-signature",
        algorithm="HS256",
    )
    res = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {legacy_token}"})
    assert res.status_code == 401


def test_signed_token_still_reads_profile(trusted_ws_issuer, game_session_upstream) -> None:
    """The profile route stays on the verified principal and accepts a Zitadel-signed token."""
    token = trusted_ws_issuer.mint("user_valeros")
    with TestClient(app) as gateway_client:
        res = gateway_client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["user_id"] == "user_valeros"
    assert "roles" not in res.json()
