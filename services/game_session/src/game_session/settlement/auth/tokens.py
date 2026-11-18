"""Zitadel OIDC token parsing and caller identity for settlement haven builder.

Governed by ADR-0005 (Zitadel OIDC Authentication), ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from runefoble_auth.principal import (
    VerifiedPrincipal,
    authenticate_authorization,
    require_principal,
)
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.config import PlatformSettings

_auth_service: ZitadelAuthService | None = None


def get_zitadel_auth_service() -> ZitadelAuthService:
    """Retrieve singleton ZitadelAuthService configured from platform settings."""
    global _auth_service
    if _auth_service is None:
        settings = PlatformSettings()
        _auth_service = ZitadelAuthService(
            issuer=settings.zitadel_issuer,
            audience=settings.zitadel_audience,
            internal_url=settings.zitadel_internal_url,
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


def decode_settlement_token(authorization: str | None = None) -> VerifiedPrincipal:
    """Verify the bearer token. Raise HTTP 401 on any failure. No fallback identity."""
    return authenticate_authorization(get_zitadel_auth_service(), authorization)


# Route identity (ADR-0015 c). Every game_session router depends on one of these.
get_caller_principal = require_principal(get_zitadel_auth_service)
CallerPrincipal = Annotated[VerifiedPrincipal, Depends(get_caller_principal)]


def get_caller_id(principal: CallerPrincipal) -> str:
    """Return the verified token subject. The only source of caller identity."""
    return principal.user_id


CallerId = Annotated[str, Depends(get_caller_id)]
