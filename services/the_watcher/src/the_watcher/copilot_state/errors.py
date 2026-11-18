"""Domain errors for the copilot aggregates and their HTTP mapping."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class CopilotStateError(Exception):
    """Base class for copilot state conflicts."""


class PendingActionNotFoundError(CopilotStateError):
    """No pending action with this id exists in the session."""


class PendingActionStateError(CopilotStateError):
    """The pending action is no longer open for a DM decision."""


async def _not_found(_request: Request, exc: CopilotStateError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def _conflict(_request: Request, exc: CopilotStateError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


def install_copilot_state_error_handlers(app: FastAPI) -> None:
    """Map a missing pending action to 404 and a closed action to 409."""
    app.add_exception_handler(PendingActionNotFoundError, _not_found)
    app.add_exception_handler(PendingActionStateError, _conflict)
