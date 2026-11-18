"""Identity dependency factory shared by every service and the gateway (ADR-0015 c, e).

A service builds its identity dependencies in three steps:

1. `make_verifier_holder(build)` returns the get and set pair for the process verifier.
   Tests replace the verifier through the set function.
2. `build_identity_dependencies(get_verifier, service_credential)` returns the route
   dependencies and their type aliases.
3. The service module binds the results to its own names.

Every service uses this module. No service keeps its own verifier copy or user-id helper.
"""

from collections.abc import Callable
from typing import Annotated, Any, NamedTuple

from fastapi import Depends
from runefoble_platform.config import PlatformSettings

from runefoble_auth.caller import CallerIdentity, require_user_or_service_credential
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.zitadel import ZitadelAuthService

VerifierGetter = Callable[[], ZitadelAuthService]
VerifierSetter = Callable[[ZitadelAuthService | None], None]


def verifier_from_settings(settings: PlatformSettings) -> ZitadelAuthService:
    """Build the Zitadel verifier from the explicit identity settings of the platform."""
    return ZitadelAuthService(
        issuer=settings.zitadel_issuer,
        audience=settings.zitadel_audience,
        internal_url=settings.zitadel_internal_url,
    )


def make_verifier_holder(
    build: Callable[[], ZitadelAuthService],
) -> tuple[VerifierGetter, VerifierSetter]:
    """Return (get, set) for one process-wide verifier.

    `get` builds the verifier on first use with `build`. `set` replaces it. Pass None to
    reset, so the next `get` builds again.
    """
    current: ZitadelAuthService | None = None

    def get_verifier() -> ZitadelAuthService:
        nonlocal current
        if current is None:
            current = build()
        return current

    def set_verifier(service: ZitadelAuthService | None) -> None:
        nonlocal current
        current = service

    return get_verifier, set_verifier


class IdentityDependencies(NamedTuple):
    """Route dependencies and type aliases built from one verifier getter."""

    get_principal: Callable[..., VerifiedPrincipal]
    CallerPrincipal: Any
    CallerId: Any
    get_caller_or_service: Callable[..., CallerIdentity]
    CallerOrService: Any


def build_identity_dependencies(
    get_verifier: VerifierGetter,
    service_credential: str | None,
) -> IdentityDependencies:
    """Build the identity dependencies for one service.

    `service_credential` is the value that this service accepts from other services
    (ADR-0015 e). Pass None when the service receives no service calls. A None value
    refuses every service-credential request with 401. User bearer requests still work.
    """
    get_principal = require_principal(get_verifier)
    CallerPrincipal = Annotated[VerifiedPrincipal, Depends(get_principal)]

    def get_caller_id(principal: CallerPrincipal) -> str:
        return principal.user_id

    CallerId = Annotated[str, Depends(get_caller_id)]
    get_caller_or_service = require_user_or_service_credential(
        get_verifier, service_credential or ""
    )
    CallerOrService = Annotated[CallerIdentity, Depends(get_caller_or_service)]
    return IdentityDependencies(
        get_principal=get_principal,
        CallerPrincipal=CallerPrincipal,
        CallerId=CallerId,
        get_caller_or_service=get_caller_or_service,
        CallerOrService=CallerOrService,
    )


__all__ = [
    "IdentityDependencies",
    "VerifierGetter",
    "VerifierSetter",
    "build_identity_dependencies",
    "make_verifier_holder",
    "verifier_from_settings",
]
