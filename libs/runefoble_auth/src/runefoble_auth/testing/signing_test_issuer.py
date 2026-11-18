"""Test-only RS256 token issuer that mimics Zitadel signing.

Use it to mint valid tokens and to build the verifier that trusts them.
It is not a production signer. It never loads keys from the environment.
"""

from __future__ import annotations

import base64
import time
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from runefoble_auth.zitadel import ZitadelAuthService

DEFAULT_ISSUER = "http://zitadel.test"
DEFAULT_AUDIENCE = "runefoble-api"
DEFAULT_KID = "signing-test-key-1"


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, byteorder="big")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def generate_rsa_key() -> rsa.RSAPrivateKey:
    """Generate a 2048-bit RSA key. Use one key per trusted issuer."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class SigningTestIssuer:
    """Holds one RSA key and mints RS256 tokens that the matching verifier accepts."""

    def __init__(
        self,
        issuer: str = DEFAULT_ISSUER,
        audience: str = DEFAULT_AUDIENCE,
        kid: str = DEFAULT_KID,
        key: rsa.RSAPrivateKey | None = None,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.kid = kid
        self.private_key = key or generate_rsa_key()

    def jwks(self) -> dict[str, Any]:
        """Return the public key as a JWK set, as Zitadel would publish it."""
        numbers = self.private_key.public_key().public_numbers()
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": self.kid,
                    "n": _b64url_uint(numbers.n),
                    "e": _b64url_uint(numbers.e),
                }
            ]
        }

    def jwk_client(self) -> jwt.PyJWKClient:
        """Return a PyJWKClient that serves this issuer's JWK set without network access."""
        client = jwt.PyJWKClient(f"{self.issuer}/.well-known/jwks.json")
        jwks = self.jwks()
        client.fetch_data = lambda: jwks  # type: ignore[method-assign]
        return client

    def verifier(self) -> ZitadelAuthService:
        """Return a production verifier configured to trust this issuer only."""
        return ZitadelAuthService(
            issuer=self.issuer,
            audience=self.audience,
            internal_url=None,
            jwk_client=self.jwk_client(),
        )

    def mint(
        self,
        sub: str,
        *,
        audience: str | None = None,
        issuer: str | None = None,
        expires_in: int = 3600,
        username: str | None = None,
        email: str | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """Mint an RS256 access token for `sub`. Override any claim for negative tests."""
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": sub,
            "iss": issuer if issuer is not None else self.issuer,
            "aud": audience if audience is not None else self.audience,
            "iat": now,
            "exp": now + expires_in,
            "preferred_username": username or sub,
            "email": email if email is not None else f"{sub}@runefoble.local",
        }
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, self.private_key, algorithm="RS256", headers={"kid": self.kid})


__all__ = [
    "DEFAULT_AUDIENCE",
    "DEFAULT_ISSUER",
    "DEFAULT_KID",
    "SigningTestIssuer",
    "generate_rsa_key",
]
