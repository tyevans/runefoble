"""User profile routes. The gateway verifies the token and forwards to game_session.

game_session owns the profile as event-sourced state (TASK-0742, ADR-0015 a and b). The
gateway holds no profile data. A failed upstream call returns the mapping in
`upstream_errors.py`: no substitute profile is returned.

The read is a row in `ROUTES` (TASK-0822). The edit stays hand-written: it sends only the
fields that are set, and drops the null fields.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from gateway_api.auth import CallerPrincipal
from gateway_api.proxy import forward_json
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes
from pydantic import BaseModel, ConfigDict, Field

SERVICE = "game_session"
PROFILE = "/api/v1/profile"

router = APIRouter(tags=["User Profile"])

ROUTES = (
    ProxyRoute(
        "GET",
        "/api/v1/profile",
        ("api", "v1", "profile"),
        SERVICE,
        name="get_profile",
        doc="Read the caller's profile through the game_session owner.",
        principal=True,
    ),
)


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, alias="displayName")
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    bio: str | None = None
    email: str | None = None

    model_config = ConfigDict(populate_by_name=True)


@router.patch("/api/v1/profile")
async def update_profile(req: UpdateProfileRequest, request: Request, user: CallerPrincipal) -> Any:
    """Edit the caller's profile in game_session. Only the fields sent are changed."""
    return await forward_json(
        request,
        service=SERVICE,
        method="PATCH",
        path=PROFILE,
        json_body=req.model_dump(exclude_none=True),
    )


register_proxy_routes(router, ROUTES)
