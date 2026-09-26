"""Blackbox TDD Suite for TASK-0034: Zitadel Production OIDC/JWKS Token Verification Middleware."""

import base64
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from gateway_api.auth import (
    set_spicedb_client,
    set_zitadel_auth_service,
)
from gateway_api.main import app
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
from starlette.testclient import WebSocketDenialResponse

# ---------------------------------------------------------------------------
# Test Keypair & Token Generation Helpers
# ---------------------------------------------------------------------------


def generate_rsa_key():
    """Generate an RSA private key for testing."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def rsa_to_jwk(key: rsa.RSAPrivateKey, kid: str = "key-zitadel-test") -> dict[str, Any]:
    """Convert an RSA public key to standard JWK dictionary."""
    pn = key.public_key().public_numbers()

    def to_b64(val: int) -> str:
        raw_bytes = val.to_bytes((val.bit_length() + 7) // 8, byteorder="big")
        return base64.urlsafe_b64encode(raw_bytes).decode("utf-8").rstrip("=")

    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": to_b64(pn.n),
        "e": to_b64(pn.e),
    }


def create_signed_token(
    key: rsa.RSAPrivateKey,
    sub: str = "user_valeros",
    exp_offset: int = 3600,
    kid: str = "key-zitadel-test",
    aud: str = "runefoble-api",
    iss: str = "http://zitadel:8080",
    roles: list[str] | dict[str, Any] | None = None,
    preferred_username: str | None = None,
) -> str:
    """Generate an RS256-signed JWT with Zitadel claims structure."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "iss": iss,
        "aud": aud,
        "iat": now,
        "exp": now + exp_offset,
        "preferred_username": preferred_username or sub,
        "email": f"{sub}@runefoble.local",
    }
    if roles is not None:
        payload["urn:zitadel:iam:org:project:roles"] = roles

    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": kid})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_environment():
    """Set up test RSA keys, mock JWKS client, and gateway auth service in production mode."""
    valid_key = generate_rsa_key()
    attacker_key = generate_rsa_key()
    kid = "key-zitadel-prod-01"

    jwk = rsa_to_jwk(valid_key, kid=kid)
    jwks_dict = {"keys": [jwk]}

    # Configure PyJWKClient with local mock fetch_data
    jwk_client = jwt.PyJWKClient("http://zitadel:8080/.well-known/jwks.json")
    jwk_client.fetch_data = lambda: jwks_dict

    # Production auth service (dev_mode=False, signature & audience verified)
    auth_service = ZitadelAuthService(
        issuer="http://zitadel:8080",
        client_id="runefoble-api",
        dev_mode=False,
        jwk_client=jwk_client,
        verify_audience=True,
    )

    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    set_zitadel_auth_service(auth_service)

    client = TestClient(app)

    yield {
        "client": client,
        "valid_key": valid_key,
        "attacker_key": attacker_key,
        "kid": kid,
        "auth_service": auth_service,
        "spicedb": mock_spicedb,
    }

    # Teardown
    set_spicedb_client(SpiceDBClient())
    set_zitadel_auth_service(None)


# ---------------------------------------------------------------------------
# HTTP Route Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_http_valid_signed_token_succeeds_and_extracts_subject(auth_environment):
    """Frontdoor test: Valid RS256 token passes verification, extracts user_id, and checks Zanzibar."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]
    spicedb = auth_environment["spicedb"]

    campaign_id = "camp-jwks-valid-01"
    user_id = "user_valeros_fighter"

    # Grant Zanzibar view permission on the campaign to this user
    await spicedb.write_relationship("campaign", campaign_id, "view", "user", user_id)

    token = create_signed_token(
        valid_key,
        sub=user_id,
        kid=kid,
        roles=["player"],
        preferred_username="Valeros",
    )

    # 1. Access protected session proxy
    res = client.get(
        f"/api/v1/sessions/{campaign_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["id"] == campaign_id

    # 2. Access profile endpoint
    profile_res = client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_res.status_code == 200
    profile = profile_res.json()
    assert profile["user_id"] == user_id
    assert profile["username"] == "Valeros"
    assert "player" in profile["roles"]


def test_http_forged_signature_rejected_401(auth_environment):
    """Frontdoor test: RS256 token signed by attacker key is rejected with 401 Unauthorized."""
    client = auth_environment["client"]
    attacker_key = auth_environment["attacker_key"]
    kid = auth_environment["kid"]

    forged_token = create_signed_token(
        attacker_key,
        sub="user_malicious",
        kid=kid,
    )

    # Protected session endpoint
    res = client.get(
        "/api/v1/sessions/camp-any",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert res.status_code == 401
    assert "Token verification failed" in res.json()["detail"]["message"]

    # Profile endpoint
    res_profile = client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert res_profile.status_code == 401


def test_http_expired_token_rejected_401(auth_environment):
    """Frontdoor test: Expired RS256 token is rejected with 401 Unauthorized."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]

    expired_token = create_signed_token(
        valid_key,
        sub="user_valeros",
        exp_offset=-300,  # Expired 5 minutes ago
        kid=kid,
    )

    res = client.get(
        "/api/v1/sessions/camp-any",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert "Signature has expired" in res.json()["detail"]["message"]


def test_http_tampered_token_rejected_401(auth_environment):
    """Frontdoor test: Tampered token string is rejected with 401 Unauthorized."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]

    token = create_signed_token(valid_key, sub="user_valeros", kid=kid)
    tampered_token = token[:-8] + "ABCDEFGH"

    res = client.get(
        "/api/v1/sessions/camp-any",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res.status_code == 401


def test_http_spoofed_x_user_id_rejected_in_production(auth_environment):
    """Frontdoor test: Spoofed X-User-Id header without valid Bearer token is rejected with 401."""
    client = auth_environment["client"]

    # Attempt to spoof identity via X-User-Id in production mode
    res = client.get(
        "/api/v1/sessions/camp-any",
        headers={"X-User-Id": "spoofed_admin"},
    )
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]["message"]


def test_http_invalid_audience_rejected_401(auth_environment):
    """Frontdoor test: Token with mismatched audience claim is rejected with 401 Unauthorized."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]

    wrong_aud_token = create_signed_token(
        valid_key,
        sub="user_valeros",
        aud="wrong-audience",
        kid=kid,
    )

    res = client.get(
        "/api/v1/sessions/camp-any",
        headers={"Authorization": f"Bearer {wrong_aud_token}"},
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# WebSocket Route Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_websocket_valid_signed_token_in_query_succeeds(auth_environment):
    """Frontdoor test: Valid signed token in WebSocket query parameter connects successfully."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]
    spicedb = auth_environment["spicedb"]

    campaign_id = "camp-ws-valid-01"
    user_id = "ws_user_kyra"

    await spicedb.write_relationship("campaign", campaign_id, "view", "user", user_id)

    token = create_signed_token(valid_key, sub=user_id, kid=kid)

    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["campaign_id"] == campaign_id
        assert msg["user_id"] == user_id


@pytest.mark.asyncio
async def test_websocket_valid_signed_token_in_header_succeeds(auth_environment):
    """Frontdoor test: Valid signed token in WebSocket Authorization header connects successfully."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]
    spicedb = auth_environment["spicedb"]

    campaign_id = "camp-ws-valid-02"
    user_id = "ws_user_merisiel"

    await spicedb.write_relationship("campaign", campaign_id, "view", "user", user_id)

    token = create_signed_token(valid_key, sub=user_id, kid=kid)

    with client.websocket_connect(
        f"/ws/campaigns/{campaign_id}",
        headers={"Authorization": f"Bearer {token}"},
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["user_id"] == user_id


def test_websocket_forged_signature_rejected_401(auth_environment):
    """Frontdoor test: Forged token in WebSocket connection is rejected with 401 Unauthorized."""
    client = auth_environment["client"]
    attacker_key = auth_environment["attacker_key"]
    kid = auth_environment["kid"]

    forged_token = create_signed_token(attacker_key, sub="ws_attacker", kid=kid)

    with (
        pytest.raises(WebSocketDenialResponse) as exc_info,
        client.websocket_connect(f"/ws/campaigns/camp-ws?token={forged_token}"),
    ):
        pass

    assert exc_info.value.status_code == 401


def test_websocket_expired_token_rejected_401(auth_environment):
    """Frontdoor test: Expired token in WebSocket connection is rejected with 401 Unauthorized."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]

    expired_token = create_signed_token(valid_key, sub="ws_user", exp_offset=-60, kid=kid)

    with (
        pytest.raises(WebSocketDenialResponse) as exc_info,
        client.websocket_connect(f"/ws/campaigns/camp-ws?token={expired_token}"),
    ):
        pass

    assert exc_info.value.status_code == 401


def test_websocket_missing_token_rejected_in_production(auth_environment):
    """Frontdoor test: Missing token in WebSocket handshake in production mode is rejected with 401."""
    client = auth_environment["client"]

    with (
        pytest.raises(WebSocketDenialResponse) as exc_info,
        client.websocket_connect("/ws/campaigns/camp-ws?user_id=spoofed_user"),
    ):
        pass

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Dev Mode Bypass Tests
# ---------------------------------------------------------------------------


def test_dev_mode_mock_bypass():
    """Verify offline dev mode preserves mock bypass without contacting JWKS."""
    auth_service = ZitadelAuthService(dev_mode=True)

    # 1. Unverified token decodes claims directly in dev mode
    payload = {"sub": "offline-hero", "preferred_username": "Hero", "email": "hero@runefoble.local"}
    dummy_jwt = jwt.encode(payload, "super-secret-development-key-32b", algorithm="HS256")
    user = auth_service.verify_token(dummy_jwt)
    assert user.user_id == "offline-hero"
    assert user.username == "Hero"

    # 2. Non-JWT mock token falls back to dev-user-001
    fallback_user = auth_service.verify_token("invalid-raw-token")
    assert fallback_user.user_id == "dev-user-001"
    assert fallback_user.username == "DevAdventurer"
