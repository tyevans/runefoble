"""Zitadel access-token verifier. The only identity verifier in the platform.

Every token must pass: RS256 signature against the issuer's JWKS, `exp`,
`sub`, `iss` (exact match), and `aud` (exact match). No mode disables any
check. No code path decodes a token without verifying it.

Inside a cluster, the browser-facing issuer host is not resolvable from a pod.
When `internal_url` is set, discovery and JWKS requests go to `internal_url`
with a `Host` header that names the issuer host. The `iss` check still uses the
issuer exactly as Zitadel writes it into the token.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any
from urllib.parse import urlsplit

import jwt
from runefoble_platform.errors import ConfigurationError

from runefoble_auth.principal import TokenVerificationError, VerifiedPrincipal

logger = logging.getLogger("runefoble.auth.zitadel")

ACCEPTED_ALGORITHMS: tuple[str, ...] = ("RS256",)
REQUIRED_CLAIMS: tuple[str, ...] = ("exp", "sub", "iss", "aud")
DISCOVERY_PATH = "/.well-known/openid-configuration"
DISCOVERY_TIMEOUT_SECONDS = 5


def _get_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=DISCOVERY_TIMEOUT_SECONDS) as response:
        document: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    return document


def discover_jwks_url(issuer: str, internal_url: str | None = None) -> str:
    """Read `jwks_uri` from the issuer's OIDC discovery document.

    With `internal_url`, the document is read from that origin with a `Host` header
    that names the issuer host. The returned `jwks_uri` is rebased onto `internal_url`.
    """
    if internal_url is None:
        url = f"{issuer.rstrip('/')}{DISCOVERY_PATH}"
        document = _get_json(url, {})
    else:
        url = f"{internal_url.rstrip('/')}{DISCOVERY_PATH}"
        document = _get_json(url, issuer_host_headers(issuer))
    jwks_uri = document.get("jwks_uri")
    if not isinstance(jwks_uri, str) or not jwks_uri:
        raise TokenVerificationError(f"Discovery document at {url} has no jwks_uri")
    if internal_url is None:
        return jwks_uri
    return _rebase(jwks_uri, internal_url)


def issuer_host_headers(issuer: str) -> dict[str, str]:
    """The `Host` header that Zitadel needs to resolve the instance for `issuer`."""
    return {"Host": urlsplit(issuer).netloc}


def _rebase(url: str, origin: str) -> str:
    parts = urlsplit(url)
    rebased = f"{origin.rstrip('/')}{parts.path}"
    return f"{rebased}?{parts.query}" if parts.query else rebased


class ZitadelAuthService:
    """Verifies Zitadel access tokens against the issuer's signing keys.

    `issuer`, `audience`, and `internal_url` have no defaults. Build the verifier from
    explicit settings (see `runefoble_auth.wiring`). A blank issuer or audience fails here,
    at start-up, not on the first request.
    """

    def __init__(
        self,
        issuer: str,
        audience: str,
        internal_url: str | None,
        jwks_cache_ttl: float = 300,
        jwk_client: jwt.PyJWKClient | None = None,
    ) -> None:
        if not issuer.strip():
            raise ConfigurationError("Zitadel issuer is not set (RUNEFOBLE_ZITADEL_ISSUER)")
        if not audience.strip():
            raise ConfigurationError("Zitadel audience is not set (RUNEFOBLE_ZITADEL_AUDIENCE)")
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.internal_url = internal_url.rstrip("/") if internal_url else None
        self.jwks_cache_ttl = jwks_cache_ttl
        self._jwks_url: str | None = None
        self._jwk_client = jwk_client

    @property
    def request_headers(self) -> dict[str, str]:
        """Headers for discovery and JWKS requests. Empty unless `internal_url` is set."""
        return issuer_host_headers(self.issuer) if self.internal_url else {}

    @property
    def jwks_url(self) -> str:
        """JWKS URL advertised by OIDC discovery, reached through `internal_url` when set."""
        if self._jwks_url is None:
            self._jwks_url = discover_jwks_url(self.issuer, self.internal_url)
        return self._jwks_url

    @property
    def jwk_client(self) -> jwt.PyJWKClient:
        if self._jwk_client is None:
            self._jwk_client = jwt.PyJWKClient(
                self.jwks_url,
                cache_jwk_set=True,
                lifespan=self.jwks_cache_ttl,
                headers=self.request_headers,
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
    username = payload.get("preferred_username") or None
    email = payload.get("email") or None
    return VerifiedPrincipal(
        user_id=subject,
        username=str(username) if username else None,
        email=str(email) if email else None,
    )
