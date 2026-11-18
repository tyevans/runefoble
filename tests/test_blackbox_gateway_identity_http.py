"""Blackbox frontdoor tests: gateway HTTP routes accept identity only from a verified bearer token.

Part of TASK-0521. Governing ADRs: ADR-0001 (SpiceDB Zanzibar), ADR-0015 (decision c: every
service verifies Zitadel JWTs itself). Hard Invariant 7: tests use public HTTP routes only.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES

ALLOWED_ORIGIN = "http://localhost:5173"
FOREIGN_ORIGIN = "https://attacker.example"


@pytest.fixture
def client(
    game_session_upstream, voice_agent_upstream, asset_forge_upstream
) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _bearer(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


# --- 1. Unauthenticated and forged requests are refused ---


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/v1/profile", None),
        ("POST", "/api/v1/campaigns", {"title": "Ghost Campaign", "setting": "Nowhere"}),
        ("POST", "/api/v1/campaigns/camp-x/roles", {"user_id": "user-x", "role": "player"}),
        (
            "POST",
            "/api/v1/mobile/companion/sess-x/whisper",
            {"recipient_id": "user-x", "content": "psst"},
        ),
    ],
)
def test_identity_routes_refuse_missing_bearer(client, method, path, body):
    response = client.request(method, path, json=body)
    assert response.status_code == 401, response.text
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.parametrize("header", ["Bearer not-a-real-jwt", "Basic dXNlcjpwYXNz", "Bearer "])
def test_profile_refuses_forged_or_malformed_authorization(client, header, trusted_ws_issuer):
    response = client.get("/api/v1/profile", headers={"Authorization": header})
    assert response.status_code == 401, response.text


def test_profile_refuses_token_signed_by_untrusted_key(client, trusted_ws_issuer):
    forged = SigningTestIssuer(issuer=trusted_ws_issuer.issuer, kid=trusted_ws_issuer.kid)
    response = client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {forged.mint('user-admin')}"},
    )
    assert response.status_code == 401, response.text


def test_asset_upload_refuses_missing_bearer(client):
    response = client.post(
        "/api/v1/assets/upload",
        files={"file": ("ghost.png", PNG_SAMPLE_BYTES, "image/png")},
    )
    assert response.status_code == 401, response.text


def test_asset_upload_refuses_x_user_id_without_bearer(client):
    response = client.post(
        "/api/v1/assets/upload",
        files={"file": ("ghost.png", PNG_SAMPLE_BYTES, "image/png")},
        headers={"X-User-Id": "user-admin"},
    )
    assert response.status_code == 401, response.text


# --- 2. A verified token is the only identity source ---


def test_profile_subject_comes_from_token_not_header(client, trusted_ws_issuer):
    response = client.get(
        "/api/v1/profile",
        headers=_bearer(trusted_ws_issuer, "user-alice") | {"X-User-Id": "someone-else"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["user_id"] == "user-alice"


def test_profile_has_no_admin_or_role_claims(client, trusted_ws_issuer):
    response = client.get("/api/v1/profile", headers=_bearer(trusted_ws_issuer, "user-alice"))
    assert response.status_code == 200, response.text
    assert "is_admin" not in response.json()
    assert "roles" not in response.json()


def test_asset_upload_owner_is_token_subject(client, trusted_ws_issuer):
    response = client.post(
        "/api/v1/assets/upload",
        files={"file": ("alice.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"owner_id": "user-bob", "asset_type": "avatar"},
        headers=_bearer(trusted_ws_issuer, "user-alice") | {"X-User-Id": "user-bob"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["owner_id"] == "user-alice"


# --- 3. CORS admits only the explicit origin list ---


def test_cors_admits_listed_origin(client):
    response = client.options(
        "/api/v1/profile",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


def test_cors_refuses_unlisted_origin(client):
    response = client.options(
        "/api/v1/profile",
        headers={
            "Origin": FOREIGN_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers
