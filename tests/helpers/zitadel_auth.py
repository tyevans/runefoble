"""Shared Zitadel OIDC test keypair generators and JWKS fixtures.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0007: Real-Time Voice and Board Synchronization
"""

from __future__ import annotations

import base64
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from gateway_api.auth import set_spicedb_client, set_zitadel_auth_service
from gateway_api.main import app
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService


def generate_rsa_key() -> rsa.RSAPrivateKey:
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
