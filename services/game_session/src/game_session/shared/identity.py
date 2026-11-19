"""Route identity for every game session router (ADR-0021 D2).

Zitadel OIDC bearer tokens and the service credential resolve to a caller.
Governed by ADR-0005 (Zitadel OIDC Authentication), ADR-0015 (c, e), and ADR-0021.
"""

from __future__ import annotations

from runefoble_auth.wiring import (
    build_identity_dependencies,
    make_verifier_holder,
    verifier_from_settings,
)
from runefoble_platform.config import PlatformSettings
from runefoble_platform.service_credential import expected_service_credential

get_zitadel_auth_service, set_zitadel_auth_service = make_verifier_holder(
    lambda: verifier_from_settings(PlatformSettings())
)


# Route identity (ADR-0015 c, e). Every game_session router depends on one of these.
# The service credential is read once at import, so a service without it never starts.
SERVICE_CREDENTIAL = expected_service_credential()
get_principal, CallerPrincipal, CallerId, get_caller_or_service, CallerOrService = (
    build_identity_dependencies(get_zitadel_auth_service, SERVICE_CREDENTIAL)
)
