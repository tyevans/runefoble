"""Roster views: character state with its owner, and the list and view rules (TASK-0585).

character_sheet owns the character aggregate, the owner relation and the list of characters
a caller may view. The gateway forwards these routes and shapes the public response.
"""

from __future__ import annotations

import logging
from uuid import UUID

from character_sheet.aggregate import CharacterAggregate
from character_sheet.models import CharacterState
from fastapi import HTTPException
from runefoble_auth.port import SpiceDBPort
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.event_sourcing import AggregateRepository

logger = logging.getLogger("runefoble.character_sheet.roster")


class CharacterRosterView(CharacterState):
    """Character state plus the SpiceDB owner. Returned by every roster route."""

    owner_id: str | None = None


async def owner_of(spicedb: SpiceDBPort, character_id: str) -> str | None:
    """Return the subject id of the character's `owner` relation, or None when unset."""
    rels = await spicedb.read_relationships(
        resource_type="character", resource_id=character_id, relation="owner"
    )
    return rels[0].subject_id if rels else None


async def roster_view(
    spicedb: SpiceDBPort, state: CharacterState, owner_id: str | None = None
) -> CharacterRosterView:
    """Attach the owner to the state. Read the owner from SpiceDB unless the caller knows it."""
    owner = owner_id if owner_id is not None else await owner_of(spicedb, str(state.character_id))
    return CharacterRosterView.model_validate({**state.model_dump(), "owner_id": owner})


async def visible_characters(
    repo: AggregateRepository[CharacterAggregate],
    spicedb: SpiceDBPort,
    user_id: str,
    campaign_id: str | None,
) -> list[CharacterRosterView]:
    """List the characters where SpiceDB grants the caller `view`, optionally one campaign."""
    character_ids = await spicedb.lookup_resources("character", "view", "user", user_id)
    views: list[CharacterRosterView] = []
    for raw_id in sorted(character_ids):
        try:
            character_uuid = UUID(raw_id)
        except ValueError:
            logger.warning("SpiceDB grants view on non-UUID character id %s. Skipped.", raw_id)
            continue
        aggregate = await load_if_exists(repo, character_uuid)
        if aggregate is None:
            logger.warning("SpiceDB grants view on character %s with no aggregate", raw_id)
            continue
        state = aggregate.state
        if campaign_id and state.campaign_id != campaign_id:
            continue
        views.append(await roster_view(spicedb, state))
    return views


def permission_denied(user_id: str, permission: str, character_id: str) -> HTTPException:
    """Build the 403 body that the gateway passes through unchanged."""
    return HTTPException(
        status_code=403,
        detail={
            "error": "permission_denied",
            "message": (
                f"Subject 'user:{user_id}' lacks '{permission}' on 'character:{character_id}'."
            ),
        },
    )
