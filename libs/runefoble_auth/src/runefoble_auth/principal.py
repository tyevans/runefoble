"""Verified principal model and the FastAPI dependency that produces it.

A principal exists only after a bearer token passes signature, issuer,
audience, expiry, and subject checks. Roles and admin flags are not part
of the principal: roles are not authority (see Hard Invariant 1).
"""

from collections.abc import Callable
from typing import Annotated, Protocol

from fastapi import Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict

UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


class TokenVerificationError(Exception):
    """Raised when a bearer token fails verification. The message is for logs only."""


class VerifiedPrincipal(BaseModel):
    """An identity whose bearer token has passed full verification."""

    model_config = ConfigDict(frozen=True)

    user_id: str
    username: str
    email: str | None = None


class BearerVerifier(Protocol):
    """Anything that turns a raw bearer token into a verified principal."""

    def verify_token(self, token: str) -> VerifiedPrincipal: ...


def bearer_token_from_authorization(authorization: str | None) -> str | None:
    """Return the token from an `Authorization: Bearer <token>` value, or None."""
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme != "Bearer":
        return None
    token = value.strip()
    return token or None


def unauthorized(message: str) -> HTTPException:
    """Build the 401 response shared by all identity entry points."""
    return HTTPException(
        status_code=401,
        detail={"error": "unauthorized", "message": message},
        headers=UNAUTHORIZED_HEADERS,
    )


def authenticate_authorization(
    verifier: BearerVerifier, authorization: str | None
) -> VerifiedPrincipal:
    """Verify the Authorization header. Raise a 401 on any failure. No fallback."""
    token = bearer_token_from_authorization(authorization)
    if token is None:
        raise unauthorized("Missing or invalid Bearer token")
    try:
        return verifier.verify_token(token)
    except TokenVerificationError as exc:
        raise unauthorized(f"Token verification failed: {exc}") from exc


def require_principal(
    get_verifier: Callable[[], BearerVerifier],
) -> Callable[..., VerifiedPrincipal]:
    """Build a FastAPI dependency that yields the verified principal for a request.

    The dependency is synchronous on purpose. FastAPI runs it in a worker
    thread, so a JWKS fetch never blocks the event loop.
    """

    def _dependency(
        request: Request,
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    ) -> VerifiedPrincipal:
        principal = authenticate_authorization(get_verifier(), authorization)
        request.state.principal = principal
        return principal

    return _dependency
