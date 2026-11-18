"""Verified caller identity for Campaign Lore routes.

Every campaign-lore route takes its caller from a verified bearer token (ADR-0015 c,
TASK-0531). No body field, query parameter, or identity header names the caller.
Roles are not authority: permission checks run through SpiceDB (Hard Invariant 1).
"""

from __future__ import annotations

from runefoble_auth.wiring import (
    build_identity_dependencies,
    make_verifier_holder,
    verifier_from_settings,
)
from runefoble_platform.config import PlatformSettings

get_zitadel_auth_service, set_zitadel_auth_service = make_verifier_holder(
    lambda: verifier_from_settings(PlatformSettings())
)
get_principal, CallerPrincipal, CallerId, get_caller_or_service, CallerOrService = (
    build_identity_dependencies(get_zitadel_auth_service, None)
)
