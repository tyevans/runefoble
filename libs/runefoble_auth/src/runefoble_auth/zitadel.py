"""Zitadel access-token verifier. The only identity verifier in the platform.

Every token must pass: RS256 signature against the issuer's JWKS, `exp`,
`sub`, `iss` (exact match), and `aud` (exact match). No mode disables any
check. No code path decodes a token without verifying it.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

import jwt

from runefoble_auth.principal import TokenVerificationError, VerifiedPrincipal

logger = logging.getLogger("runefoble.auth.zitadel")

ACCEPTED_ALGORITHMS: tuple[str, ...] = ("RS256",)
REQUIRED_CLAIMS: tuple[str, ...] = ("exp", "sub", "iss", "aud")
DISCOVERY_PATH = "/.well-known/openid-configuration"
DISCOVERY_TIMEOUT_SECONDS = 5


def discover_jwks_url(issuer: str) -> str:
    """Read `jwks_uri` from the issuer's OIDC discovery document."""
    url = f"{issuer.rstrip('/')}{DISCOVERY_PATH}"
    with urllib.request.urlopen(url, timeout=DISCOVERY_TIMEOUT_SECONDS) as response:
        document: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    jwks_uri = document.get("jwks_uri")
    if not isinstance(jwks_uri, str) or not jwks_uri:
        raise TokenVerificationError(f"Discovery document at {url} has no jwks_uri")
    return jwks_uri


class ZitadelAuthService:
    """Verifies Zitadel access tokens against the issuer's signing keys."""

    def __init__(
        self,
        issuer: str = "http://localhost:8080",
        audience: str = "runefoble-api",
        jwks_url: str | None = None,
        jwks_cache_ttl: float = 300,
        jwk_client: jwt.PyJWKClient | None = None,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.jwks_cache_ttl = jwks_cache_ttl
        self._jwks_url = jwks_url
        self._jwk_client = jwk_client

    @property
    def jwks_url(self) -> str:
        """Configured JWKS URL, or the `jwks_uri` advertised by OIDC discovery."""
        if self._jwks_url is None:
            self._jwks_url = discover_jwks_url(self.issuer)
        return self._jwks_url

    @property
    def jwk_client(self) -> jwt.PyJWKClient:
        if self._jwk_client is None:
            self._jwk_client = jwt.PyJWKClient(
                self.jwks_url,
                cache_jwk_set=True,
                lifespan=self.jwks_cache_ttl,
            )
        return self._jwk_client

    def verify_token(self, token: str, audience: str | None = None) -> VerifiedPrincipal:
        """Verify a bearer token and return the principal it identifies.

        `audience` overrides the configured audience for one call. Leave it
        unset in production code.
        """
        expected_audience = audience or self.audience
        try:
            signing_key = self.jwk_client.get_signing_key_from_jwt(token)
            payload: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=list(ACCEPTED_ALGORITHMS),
                audience=expected_audience,
                issuer=self.issuer,
                options={"require": list(REQUIRED_CLAIMS)},
            )
        except jwt.PyJWTError as exc:
            logger.warning("Token rejected: %s", exc)
            raise TokenVerificationError(str(exc)) from exc
        return _principal_from_claims(payload)


def _principal_from_claims(payload: dict[str, Any]) -> VerifiedPrincipal:
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise TokenVerificationError("Token 'sub' claim is empty or not a string")
    username = payload.get("preferred_username") or subject
    email = payload.get("email") or None
    return VerifiedPrincipal(
        user_id=subject,
        username=str(username),
        email=str(email) if email else None,
    )
