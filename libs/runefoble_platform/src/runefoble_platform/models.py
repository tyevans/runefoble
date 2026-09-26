"""Core domain and platform models."""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class BaseEntity(BaseModel):
    """Base class for all persisted domain entities."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CampaignScopedEntity(BaseEntity):
    """Entity belonging to a specific campaign."""

    campaign_id: str
    tenant_id: str | None = None


class UserPrincipal(BaseModel):
    """Authenticated user context passed across services."""

    user_id: str
    email: str
    roles: list[str] = Field(default_factory=list)
    active_campaign_id: str | None = None
