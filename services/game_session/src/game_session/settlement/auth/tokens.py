"""Zitadel OIDC token parsing and caller identity for settlement haven builder.

Governed by ADR-0005 (Zitadel OIDC Authentication), ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from runefoble_auth.zitadel import AuthenticatedUser, ZitadelAuthService
from runefoble_platform.config import PlatformSettings

logger = logging.getLogger("runefoble.game_session.settlement.auth.tokens")
_auth_service: ZitadelAuthService | None = None


def get_zitadel_auth_service() -> ZitadelAuthService:
    """Retrieve singleton ZitadelAuthService configured from platform settings."""
    global _auth_service
    if _auth_service is None:
        settings = PlatformSettings()
        _auth_service = ZitadelAuthService(
            issuer=settings.zitadel_issuer,
            client_id=settings.zitadel_client_id,
            jwks_url=settings.zitadel_jwks_url,
            dev_mode=settings.auth_dev_mode,
        )
    return _auth_service


def set_zitadel_auth_service(service: ZitadelAuthService | None) -> None:
    """Override singleton ZitadelAuthService for tests."""
    global _auth_service
    _auth_service = service


def extract_bearer_token(authorization: str | None) -> str | None:
    """Extract raw bearer token string from HTTP Authorization header value."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:].strip()
    return None


def decode_settlement_token(
    authorization: str | None = None,
    x_user_id: str | None = None,
) -> AuthenticatedUser:
    """Verify Zitadel bearer token or fallback to local mock user in dev/test mode."""
    auth_service = get_zitadel_auth_service()
    token = extract_bearer_token(authorization)
    if token:
        try:
            return auth_service.verify_token(token)
        except Exception as exc:
            logger.warning("Bearer token verification failed: %s", exc)
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized", "message": f"Token verification failed: {exc}"},
            ) from exc

    if auth_service.dev_mode:
        uid = x_user_id or "dev-user-001"
        return AuthenticatedUser(
            user_id=uid,
            username=uid,
            roles=["player", "dm"],
            is_admin=True,
        )

    raise HTTPException(
        status_code=401,
        detail={"error": "unauthorized", "message": "Missing or invalid Bearer token"},
    )
