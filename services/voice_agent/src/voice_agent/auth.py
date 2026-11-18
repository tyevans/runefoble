"""Verified caller identity for voice_agent HTTP and WebSocket routes.

Governed by ADR-0015 decision (c): every service verifies the Zitadel JWT itself.
Identity comes only from a verified bearer token. No header, query string, or
default value supplies a subject. Permission checks use the verified subject.
"""

from __future__ import annotations

from runefoble_auth.wiring import (
    build_identity_dependencies,
    make_verifier_holder,
    verifier_from_settings,
)
from runefoble_platform.config import PlatformSettings

get_voice_verifier, set_voice_verifier = make_verifier_holder(
    lambda: verifier_from_settings(PlatformSettings())
)
get_principal, CallerPrincipal, CallerId, get_caller_or_service, CallerOrService = (
    build_identity_dependencies(get_voice_verifier, None)
)


def caller_headers(authorization: str | None) -> dict[str, str]:
    """Return the headers that forward the speaker's own bearer to a downstream service.

    The downstream service verifies the token itself. No identity is set here.
    """
    return {"Authorization": authorization} if authorization else {}


__all__ = [
    "CallerId",
    "CallerPrincipal",
    "caller_headers",
    "get_principal",
    "get_voice_verifier",
    "set_voice_verifier",
]
