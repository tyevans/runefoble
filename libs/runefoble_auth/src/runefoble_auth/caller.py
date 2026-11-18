"""Caller identity for routes that accept a user bearer or the service credential (ADR-0015 c, e).

A request that presents an `Authorization` header must verify as a Zitadel user token.
A failed user token is a 401 even when the service credential is also present.
A request with no `Authorization` header is a service call when it presents the service
credential. A service call has no user id. Routes that act for a user must not use this
dependency. They keep `require_principal`, so a service call cannot take a user's action.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header
from runefoble_platform.service_credential import (
    SERVICE_CREDENTIAL_HEADER,
    service_credential_matches,
)

from runefoble_auth.principal import BearerVerifier, authenticate_authorization, unauthorized


@dataclass(frozen=True)
class CallerIdentity:
    """Who made the call. `user_id` is None for a service call with no on-behalf-of user."""

    user_id: str | None
    via_service_credential: bool


def require_user_or_service_credential(
    get_verifier: Callable[[], BearerVerifier],
    expected_credential: str,
) -> Callable[..., CallerIdentity]:
    """Build a dependency that accepts a verified user bearer or the service credential."""

    def _dependency(
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
        service_credential: Annotated[str | None, Header(alias=SERVICE_CREDENTIAL_HEADER)] = None,
    ) -> CallerIdentity:
        if authorization is not None:
            principal = authenticate_authorization(get_verifier(), authorization)
            return CallerIdentity(user_id=principal.user_id, via_service_credential=False)
        if service_credential_matches(service_credential, expected_credential):
            return CallerIdentity(user_id=None, via_service_credential=True)
        raise unauthorized("Missing bearer token or service credential")

    return _dependency
