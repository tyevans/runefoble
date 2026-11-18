"""SpiceDB permission checks and ownership writes for character objects.

Every call fails closed. A SpiceDB error becomes a 503 response and never a denial
or a success. No write in this module is suppressed (ADR-0001).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from fastapi import HTTPException
from runefoble_auth.errors import AuthzError
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient

AuthzClient = SpiceDBClient | MockSpiceDBClient


def _authorization_unavailable(message: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"error": "authorization_unavailable", "message": message},
    )


@contextmanager
def authz_write_guard() -> Iterator[None]:
    """Turn a failed SpiceDB call into a 503. The caller never sees a success."""
    try:
        yield
    except AuthzError as exc:
        raise _authorization_unavailable("Authorization service did not apply the change.") from exc


async def authorize_character(
    spicedb: AuthzClient, character_id: UUID, permission: str, user_id: str
) -> None:
    """Allow only when SpiceDB grants `permission` on the character to the user."""
    try:
        allowed = await spicedb.check_permission(
            "character", str(character_id), permission, "user", user_id
        )
    except AuthzError as exc:
        raise _authorization_unavailable("Authorization service is unavailable.") from exc
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"User '{user_id}' does not have {permission} permission on character '{character_id}'",
        )


async def write_character_ownership(
    spicedb: AuthzClient, character_id: UUID, owner_id: str, campaign_id: str | None
) -> None:
    """Write the owner tuple and, when given, the campaign tuple for a new character."""
    cid = str(character_id)
    with authz_write_guard():
        await spicedb.write_relationship("character", cid, "owner", "user", owner_id)
        if campaign_id:
            await spicedb.write_relationship("character", cid, "campaign", "campaign", campaign_id)


async def replace_character_campaign(
    spicedb: AuthzClient, character_id: UUID, campaign_id: str | None
) -> None:
    """Replace every campaign tuple of the character with the given campaign, or none."""
    cid = str(character_id)
    with authz_write_guard():
        existing = await spicedb.read_relationships(
            resource_type="character", resource_id=cid, relation="campaign"
        )
        for rel in existing:
            await spicedb.delete_relationship(
                "character", cid, "campaign", rel.subject_type, rel.subject_id
            )
        if campaign_id:
            await spicedb.write_relationship("character", cid, "campaign", "campaign", campaign_id)
