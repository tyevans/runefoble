"""SpiceDB permission checks and ownership writes for character objects.

Every call fails closed. A SpiceDB error propagates as `AuthzError`, and the service maps it to
503 (`runefoble_auth.authz_http`). No write in this module is suppressed (ADR-0001).
"""

from __future__ import annotations

from uuid import UUID

from character_sheet.roster import permission_denied
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_auth.spicedb import SpiceDBClient

AuthzClient = SpiceDBClient | MockSpiceDBClient


async def authorize_character(
    spicedb: AuthzClient, character_id: UUID, permission: str, user_id: str
) -> None:
    """Allow only when SpiceDB grants `permission` on the character to the user."""
    allowed = await spicedb.check_permission(
        "character", str(character_id), permission, "user", user_id
    )
    if not allowed:
        raise permission_denied(user_id, permission, str(character_id))


async def write_character_ownership(
    spicedb: AuthzClient, character_id: UUID, owner_id: str, campaign_id: str | None
) -> None:
    """Write the owner tuple and, when given, the campaign tuple for a new character."""
    cid = str(character_id)
    await spicedb.write_relationship("character", cid, "owner", "user", owner_id)
    if campaign_id:
        await spicedb.write_relationship("character", cid, "campaign", "campaign", campaign_id)


async def replace_character_campaign(
    spicedb: AuthzClient, character_id: UUID, campaign_id: str | None
) -> None:
    """Replace every campaign tuple of the character with the given campaign, or none."""
    cid = str(character_id)
    existing = await spicedb.read_relationships(
        resource_type="character", resource_id=cid, relation="campaign"
    )
    for rel in existing:
        await spicedb.delete_relationship(
            "character", cid, "campaign", rel.subject_type, rel.subject_id
        )
    if campaign_id:
        await spicedb.write_relationship("character", cid, "campaign", "campaign", campaign_id)
