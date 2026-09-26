"""Zitadel OIDC and JWT token authentication helper."""

import logging
import os
from typing import Any

import jwt
from pydantic import BaseModel

logger = logging.getLogger("runefoble.auth.zitadel")


class TokenVerificationError(jwt.PyJWTError):
    """Raised when JWT verification against Zitadel fails."""


class AuthenticatedUser(BaseModel):
    user_id: str
    username: str
    email: str | None = None
    roles: list[str] = []
    is_admin: bool = False


class ZitadelAuthService:
    """Validates tokens and provides user claims against self-hosted Zitadel."""

    def __init__(
        self,
        issuer: str = "http://localhost:8080",
        client_id: str = "runefoble-api",
        jwks_url: str | None = None,
        jwks_cache_ttl: float = 300,
        dev_mode: bool | None = None,
        jwk_client: jwt.PyJWKClient | None = None,
        verify_audience: bool = False,
        audience: str | None = None,
        verify_issuer: bool = False,
    ):
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.jwks_url = jwks_url or f"{self.issuer}/.well-known/jwks.json"
        self.jwks_cache_ttl = jwks_cache_ttl
        self.verify_audience = verify_audience
        self.audience = audience or client_id
        self.verify_issuer = verify_issuer

        if dev_mode is not None:
            self.dev_mode = dev_mode
        else:
            self.dev_mode = os.environ.get("RUNEFOBLE_AUTH_DEV_MODE", "true").lower() in (
                "true",
                "1",
                "yes",
            )

        self._jwk_client = jwk_client

    @property
    def jwk_client(self) -> jwt.PyJWKClient:
        if self._jwk_client is None:
            self._jwk_client = jwt.PyJWKClient(
                self.jwks_url,
                cache_jwk_set=True,
                lifespan=self.jwks_cache_ttl,
            )
        return self._jwk_client

    @jwk_client.setter
    def jwk_client(self, client: jwt.PyJWKClient | None) -> None:
        self._jwk_client = client

    def _extract_user_from_payload(self, payload: dict[str, Any]) -> AuthenticatedUser:
        user_id = payload.get("sub")
        if not user_id:
            raise TokenVerificationError("Token missing required 'sub' claim")

        email = payload.get("email")
        roles_raw = payload.get("urn:zitadel:iam:org:project:roles", [])
        if isinstance(roles_raw, dict):
            roles = list(roles_raw.keys())
        elif isinstance(roles_raw, list):
            roles = [str(r) for r in roles_raw]
        else:
            roles = []

        username = payload.get("preferred_username", user_id)
        return AuthenticatedUser(
            user_id=str(user_id),
            username=str(username),
            email=str(email) if email else None,
            roles=roles,
            is_admin="admin" in roles,
        )

    def _dev_mock_decode(self, token: str) -> AuthenticatedUser:
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_aud": False,
                    "verify_iss": False,
                },
                algorithms=["RS256", "HS256"],
            )
            return self._extract_user_from_payload(payload)
        except Exception:
            # Fallback for dev / mock tokens
            return AuthenticatedUser(
                user_id="dev-user-001",
                username="DevAdventurer",
                email="dev@runefoble.local",
                roles=["player", "dm"],
                is_admin=True,
            )

    def _verify_token_jwks(
        self,
        token: str,
        audience: str | None = None,
    ) -> AuthenticatedUser:
        try:
            signing_key = self.jwk_client.get_signing_key_from_jwt(token)
            target_audience = audience or (self.audience if self.verify_audience else None)
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": bool(target_audience),
                "verify_iss": self.verify_issuer,
            }
            decode_kwargs: dict[str, Any] = {
                "algorithms": ["RS256"],
                "options": options,
            }
            if target_audience:
                decode_kwargs["audience"] = target_audience
            if self.verify_issuer:
                decode_kwargs["issuer"] = self.issuer

            payload: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                **decode_kwargs,
            )
            return self._extract_user_from_payload(payload)
        except jwt.PyJWTError:
            raise
        except Exception as exc:
            raise TokenVerificationError(f"JWKS verification failed: {exc}") from exc

    def verify_token(
        self,
        token: str,
        *,
        verify: bool | None = None,
        audience: str | None = None,
    ) -> AuthenticatedUser:
        """Verify a Zitadel JWT token against JWKS endpoint or dev bypass."""
        should_verify = (not self.dev_mode) if verify is None else verify
        if not should_verify:
            return self._dev_mock_decode(token)
        return self._verify_token_jwks(token, audience=audience)

    def decode_token(self, token: str, verify: bool = False) -> AuthenticatedUser:
        """Decode a Zitadel JWT token into a structured user object.

        Provided for backward compatibility. In production, calls verify_token.
        """
        return self.verify_token(token, verify=verify)
