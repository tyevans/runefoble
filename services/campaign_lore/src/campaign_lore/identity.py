"""Verified caller identity for Campaign Lore routes.

Every campaign-lore route takes its caller from a verified bearer token (ADR-0015 c,
TASK-0531). No body field, query parameter, or identity header names the caller.
Roles are not authority: permission checks run through SpiceDB (Hard Invariant 1).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.config import PlatformSettings

_auth_service: ZitadelAuthService | None = None


def get_zitadel_auth_service() -> ZitadelAuthService:
    """Retrieve the singleton ZitadelAuthService configured from platform settings."""
    global _auth_service
    if _auth_service is None:
        settings = PlatformSettings()
        _auth_service = ZitadelAuthService(
            issuer=settings.zitadel_issuer,
            audience=settings.zitadel_audience,
            jwks_url=settings.zitadel_jwks_url,
        )
    return _auth_service


def set_zitadel_auth_service(service: ZitadelAuthService | None) -> None:
    """Override the singleton ZitadelAuthService for tests."""
    global _auth_service
    _auth_service = service


get_campaign_principal = require_principal(get_zitadel_auth_service)
CampaignPrincipal = Annotated[VerifiedPrincipal, Depends(get_campaign_principal)]


def get_verified_subject(principal: CampaignPrincipal) -> str:
    """Return the verified subject of the request. Never a client-supplied value."""
    return principal.user_id


CallerId = Annotated[str, Depends(get_verified_subject)]
