"""Request and response models for the owner profile routes (TASK-0742)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class UpdateProfileRequest(BaseModel):
    """Editable profile fields. A field left out, or sent as null, is not changed."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    email: str | None = None

    def changes(self) -> dict[str, str]:
        return {field: value for field, value in self.model_dump().items() if value is not None}


class ProfileResponse(BaseModel):
    """The profile a user sees. Username and email default to the verified token.

    `username` is None when the token has no username claim. `display_name` is then None
    until the user edits it.
    """

    user_id: str
    username: str | None
    email: str | None
    display_name: str | None
    avatar_url: str | None
    bio: str
