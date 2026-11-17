"""Verified caller identity for voice_agent HTTP and WebSocket routes.

Governed by ADR-0015 decision (c): every service verifies the Zitadel JWT itself.
Identity comes only from a verified bearer token. No header, query string, or
default value supplies a subject. Permission checks use the verified subject.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.config import PlatformSettings

_verifier: ZitadelAuthService | None = None


def get_voice_verifier() -> ZitadelAuthService:
    """Return the Zitadel verifier built from the platform identity settings."""
    global _verifier
    if _verifier is None:
        settings = PlatformSettings()
        _verifier = ZitadelAuthService(
            issuer=settings.zitadel_issuer,
            audience=settings.zitadel_audience,
            jwks_url=settings.zitadel_jwks_url,
        )
    return _verifier


def set_voice_verifier(service: ZitadelAuthService | None) -> None:
    """Replace the verifier. Tests use this to trust a signing issuer. Pass None to reset."""
    global _verifier
    _verifier = service


get_voice_principal = require_principal(get_voice_verifier)
VoicePrincipal = Annotated[VerifiedPrincipal, Depends(get_voice_principal)]


__all__ = [
    "VoicePrincipal",
    "get_voice_principal",
    "get_voice_verifier",
    "set_voice_verifier",
]
