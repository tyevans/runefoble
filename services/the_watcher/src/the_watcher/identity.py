"""Verified caller identity for The Watcher routes (ADR-0015 c).

Every router depends on `CallerId`. The subject of a verified Zitadel token is the only
source of caller identity. Headers, query parameters, and body fields never set it.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.config import PlatformSettings

_auth_service: ZitadelAuthService | None = None


def get_zitadel_auth_service() -> ZitadelAuthService:
    """Return the singleton Zitadel verifier built from platform settings."""
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
    """Override the verifier. Tests use this to trust a signing issuer."""
    global _auth_service
    _auth_service = service


get_caller_principal = require_principal(get_zitadel_auth_service)
CallerPrincipal = Annotated[VerifiedPrincipal, Depends(get_caller_principal)]


def get_caller_id(principal: CallerPrincipal) -> str:
    """Return the verified token subject."""
    return principal.user_id


CallerId = Annotated[str, Depends(get_caller_id)]
