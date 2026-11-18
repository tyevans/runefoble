"""Verified caller identity for The Watcher routes (ADR-0015 c).

Every router depends on `CallerId`. The subject of a verified Zitadel token is the only
source of caller identity. Headers, query parameters, and body fields never set it.
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
