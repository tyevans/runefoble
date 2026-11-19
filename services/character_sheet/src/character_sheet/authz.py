"""SpiceDB permission checks and ownership writes for character objects.

Every call fails closed. A SpiceDB error propagates as `AuthzError`, and the service maps it to
503 (`runefoble_auth.authz_http`). No write in this module is suppressed (ADR-0001).
"""

from __future__ import annotations

from uuid import UUID

from character_sheet.roster import permission_denied
from fastapi import HTTPException
from runefoble_auth.port import SpiceDBPort


def character_denial(
    resource_type: str, resource_id: str, permission: str, user_id: str
) -> HTTPException:
    """Build the character 403 body that the gateway passes through unchanged."""
    return permission_denied(user_id, permission, resource_id)


async def write_character_ownership(
    spicedb: SpiceDBPort, character_id: UUID, owner_id: str, campaign_id: str | None
) -> None:
    """Write the owner tuple and, when given, the campaign tuple for a new character."""
    cid = str(character_id)
    await spicedb.write_relationship("character", cid, "owner", "user", owner_id)
    if campaign_id:
        await spicedb.write_relationship("character", cid, "campaign", "campaign", campaign_id)


async def replace_character_campaign(
    spicedb: SpiceDBPort, character_id: UUID, campaign_id: str | None
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
