"""SpiceDB Zanzibar object-level permissions and caller identity for Campaign Lore."""

from typing import Annotated
from uuid import UUID

from fastapi import Header
from runefoble_auth.spicedb import SpiceDBClient


def get_current_user_id(
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
) -> str | None:
    """Extract authenticated caller identity from x-user-id header."""
    return x_user_id


async def check_user_can_read_secrets(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can read secret DM lore."""
    if not user_id:
        return False
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="run_session",
        subject_type="user",
        subject_id=user_id,
    )


async def check_user_can_view_campaign(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can view campaign lore."""
    if not user_id:
        return True
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="view",
        subject_type="user",
        subject_id=user_id,
    )


async def check_user_can_interact_handout(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can interact with handout."""
    if not user_id:
        return True
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="play",
        subject_type="user",
        subject_id=user_id,
    )


async def check_user_can_inspect_relic(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can view and inspect relic."""
    if not user_id:
        return True
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="view",
        subject_type="user",
        subject_id=user_id,
    )


async def check_user_can_play_campaign(
    user_id: str | None,
    campaign_id: UUID,
    spicedb: SpiceDBClient,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can play or discover in campaign."""
    if not user_id:
        return True
    can_play = await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="play",
        subject_type="user",
        subject_id=user_id,
    )
    if can_play:
        return True
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="run_session",
        subject_type="user",
        subject_id=user_id,
    )
