"""Blackbox TDD Suite for Zitadel HTTP Bearer & JWKS Token Verification Middleware.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- TASK-0034: Zitadel Production OIDC/JWKS Token Verification Middleware
- TASK-0079: Zitadel OIDC Token Verification Blackbox Test Suite Modular Decomposition
"""

import jwt
import pytest
from runefoble_auth.zitadel import ZitadelAuthService

from tests.helpers.zitadel_auth import create_signed_token


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
