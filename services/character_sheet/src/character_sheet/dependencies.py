"""Shared dependencies, aggregate repository, and event bus for Character Sheet microservice."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Annotated, Any
from uuid import UUID, uuid4

from character_sheet.aggregate import CharacterAggregate
from character_sheet.crafting import CraftingAggregate
from character_sheet.models import CharacterState
from character_sheet.schemas import CreateCharacterRequest, UpdateGuardrailsRequest
from fastapi import Depends, Header, HTTPException
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.events import StandInPolicyUpdated, StandInStabilized
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus

STREAM_CHARACTER = "runefoble.events.character"
STREAM_CRAFTING = "runefoble.events.crafting"
platform_settings = PlatformSettings()

_event_bus: RedisStreamsEventBus | None = None
_spicedb_client: SpiceDBClient = SpiceDBClient()

# Global aggregate repositories
repo: AggregateRepository[CharacterAggregate] = create_aggregate_repository(CharacterAggregate)
crafting_repo: AggregateRepository[CraftingAggregate] = create_aggregate_repository(
    CraftingAggregate
)


def get_repository() -> AggregateRepository[CharacterAggregate]:
    return repo


def get_crafting_repository() -> AggregateRepository[CraftingAggregate]:
    return crafting_repo


def get_event_bus() -> RedisStreamsEventBus | None:
    global _event_bus
    if _event_bus is None and platform_settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus


def get_spicedb_client() -> SpiceDBClient:
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient) -> None:
    global _spicedb_client
    _spicedb_client = client


RepoDep = Annotated[AggregateRepository[CharacterAggregate], Depends(get_repository)]
CraftingRepoDep = Annotated[
    AggregateRepository[CraftingAggregate], Depends(get_crafting_repository)
]
SpiceDep = Annotated[SpiceDBClient, Depends(get_spicedb_client)]
UserHeader = Annotated[str | None, Header(alias="x-user-id")]


async def publish_character_event(event: Any) -> None:
    bus = get_event_bus()
    if bus:
        with contextlib.suppress(Exception):
            await bus.publish_event(STREAM_CHARACTER, event)


async def publish_crafting_event(event: Any) -> None:
    bus = get_event_bus()
    if bus:
        with contextlib.suppress(Exception):
            await bus.publish_event(STREAM_CRAFTING, event)


async def load_character(
    repo: AggregateRepository[CharacterAggregate], character_id: UUID
) -> CharacterAggregate:
    try:
        return await repo.load(character_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Character not found: {e}") from e


async def create_new_character(
    repo: AggregateRepository[CharacterAggregate], req: CreateCharacterRequest
) -> CharacterState:
    char = CharacterAggregate(uuid4())
    char.create(req.name, req.character_class, req.max_hp, req.player_id, req.personality_traits)
    await repo.save(char)
    return char.state


async def execute_character_mutation(
    repo: AggregateRepository[CharacterAggregate],
    character_id: UUID,
    mutation_fn: Callable[[CharacterAggregate], Any],
) -> CharacterState:
    try:
        char = await repo.load(character_id)
        mutation_fn(char)
        await repo.save(char)
        return char.state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


async def modify_character_health(
    repo: AggregateRepository[CharacterAggregate],
    character_id: UUID,
    delta: int,
    source: str,
    is_stand_in: bool | None,
) -> CharacterState:
    char = await repo.load(character_id)
    was_stabilized = char.state.is_stabilized
    char.modify_health(delta=delta, source=source, is_stand_in=is_stand_in)
    await repo.save(char)
    if not was_stabilized and char.state.is_stabilized:
        await publish_character_event(
            StandInStabilized(
                aggregate_id=character_id,
                character_id=str(character_id),
                current_hp=0,
                condition="unconscious_stabilized",
            )
        )
    return char.state


async def authorize_character_edit(
    spicedb: SpiceDBClient, character_id: UUID, user_id: str | None
) -> None:
    if user_id and not await spicedb.check_permission(
        "character", str(character_id), "edit", "user", user_id
    ):
        raise HTTPException(
            status_code=403,
            detail=f"User '{user_id}' does not have edit permission on character '{character_id}'",
        )


async def update_character_guardrails(
    repo: AggregateRepository[CharacterAggregate],
    character_id: UUID,
    req: UpdateGuardrailsRequest,
) -> CharacterState:
    char = await repo.load(character_id)
    char.update_stand_in_guardrails(req)
    await repo.save(char)
    await publish_character_event(
        StandInPolicyUpdated(
            aggregate_id=character_id,
            character_id=str(character_id),
            guardrails=char.state.stand_in_guardrails.model_dump(),
        )
    )
    return char.state
