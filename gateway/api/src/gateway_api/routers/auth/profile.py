"""User profile management and claims persistence router."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from gateway_api.auth import get_current_user
from pydantic import BaseModel, ConfigDict, Field
from runefoble_auth.zitadel import AuthenticatedUser

router = APIRouter(tags=["User Profile"])

# In-memory storage for persistent user profile attributes across sessions
USER_PROFILES: dict[str, dict[str, Any]] = {}


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, alias="displayName")
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    bio: str | None = None
    email: str | None = None

    model_config = ConfigDict(populate_by_name=True)


def get_stored_profile(user: AuthenticatedUser) -> dict[str, Any]:
    stored = USER_PROFILES.setdefault(
        user.user_id,
        {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "display_name": user.username,
            "avatar_url": None,
            "bio": "",
        },
    )
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": stored.get("email", user.email),
        "display_name": stored.get("display_name", user.username),
        "avatar_url": stored.get("avatar_url", None),
        "bio": stored.get("bio", ""),
        "roles": user.roles,
        "is_admin": user.is_admin,
    }


@router.get("/api/v1/profile")
async def get_profile(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Retrieve authenticated Zitadel user profile claims and customized settings."""
    return get_stored_profile(user)


@router.patch("/api/v1/profile")
async def update_profile(
    req: UpdateProfileRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Update user profile claims (display name, avatar URL, bio)."""
    stored = USER_PROFILES.setdefault(
        user.user_id,
        {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "display_name": user.username,
            "avatar_url": None,
            "bio": "",
        },
    )
    if req.display_name is not None:
        stored["display_name"] = req.display_name
    if req.avatar_url is not None:
        stored["avatar_url"] = req.avatar_url
    if req.bio is not None:
        stored["bio"] = req.bio
    if req.email is not None:
        stored["email"] = req.email

    return get_stored_profile(user)
