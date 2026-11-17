"""Domain errors for campaign lifecycle and their HTTP mapping (ADR-0015 a, b)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class CampaignError(Exception):
    """Base error. Each subclass carries the HTTP status and a stable error code."""

    status_code: int = 400
    error: str = "campaign_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class CampaignNotFoundError(CampaignError):
    status_code = 404
    error = "campaign_not_found"


class PermissionDeniedError(CampaignError):
    status_code = 403
    error = "permission_denied"


class InvalidInviteError(CampaignError):
    status_code = 400
    error = "invalid_invite"


class InviteExpiredError(CampaignError):
    status_code = 410
    error = "invite_expired"


class InviteExhaustedError(CampaignError):
    status_code = 409
    error = "invite_exhausted"


class MemberNotFoundError(CampaignError):
    status_code = 404
    error = "member_not_found"


class OwnerNotRemovableError(CampaignError):
    status_code = 409
    error = "owner_not_removable"


class ConcurrentUpdateError(CampaignError):
    status_code = 409
    error = "concurrent_update"


class AuthorizationStoreError(CampaignError):
    """A SpiceDB tuple write or delete failed after the aggregate was saved."""

    status_code = 503
    error = "authorization_store_unavailable"


async def _campaign_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, CampaignError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"error": exc.error, "message": exc.message}},
    )


def register_campaign_error_handlers(app: FastAPI) -> None:
    """Map every CampaignError raised by the campaign routes to its HTTP response."""
    app.add_exception_handler(CampaignError, _campaign_error_handler)
