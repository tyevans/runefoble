"""Shared dependencies, aggregate repository, and event bus for Character Sheet microservice."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any
from uuid import UUID

from character_sheet.aggregate import CharacterAggregate
from character_sheet.authz import (
    character_denial,
    replace_character_campaign,
)
from character_sheet.crafting import CraftingAggregate
from character_sheet.health_events import health_change_events
from character_sheet.models import CharacterState
from character_sheet.schemas import CreateCharacterRequest
from fastapi import Depends
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_auth.permissions import require_permission
from runefoble_auth.settings import load_spicedb_settings
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.wiring import (
    build_identity_dependencies,
    make_verifier_holder,
    verifier_from_settings,
)
from runefoble_events.events import (
    CharacterAssignedToCampaign,
    StandInPolicyUpdated,
)
from runefoble_platform.aggregate_loading import load_or_404
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_publish import publish_best_effort
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.service_credential import expected_service_credential
from runefoble_platform.stand_in_guardrails import StandInGuardrailPolicy

STREAM_CHARACTER = "runefoble.events.character"
STREAM_CRAFTING = "runefoble.events.crafting"
platform_settings = PlatformSettings()
# This service checks SpiceDB permissions. Fail fast at start-up without the key (TASK-0720).
load_spicedb_settings()

# Global aggregate repositories
repo: AggregateRepository[CharacterAggregate] = create_aggregate_repository(CharacterAggregate)
crafting_repo: AggregateRepository[CraftingAggregate] = create_aggregate_repository(
    CraftingAggregate
)


def get_repository() -> AggregateRepository[CharacterAggregate]:
    return repo


def get_crafting_repository() -> AggregateRepository[CraftingAggregate]:
    return crafting_repo


event_bus_provider = EventBusProvider(platform_settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set


RepoDep = Annotated[AggregateRepository[CharacterAggregate], Depends(get_repository)]
CraftingRepoDep = Annotated[
    AggregateRepository[CraftingAggregate], Depends(get_crafting_repository)
]
SpiceDep = Annotated[SpiceDBClient | MockSpiceDBClient, Depends(get_spicedb_client)]


get_zitadel_auth_service, set_zitadel_auth_service = make_verifier_holder(
    lambda: verifier_from_settings(platform_settings)
)
SERVICE_CREDENTIAL = expected_service_credential()
get_principal, CallerPrincipal, CallerId, get_caller_or_service, CallerOrService = (
    build_identity_dependencies(get_zitadel_auth_service, SERVICE_CREDENTIAL)
)


def _character_permission(permission: str, *, allow_service: bool = False) -> list[Any]:
    """Route dependencies for one schema permission on the path's character (ADR-0001).

    A user bearer needs the permission (403 otherwise). With `allow_service`, the service
    credential passes without a user. A missing or bad credential is a 401. SpiceDB failures
    answer 503.
    """
    return [
        Depends(
            require_permission(
                "character",
                permission,
                "character_id",
                principal=get_caller_or_service if allow_service else get_principal,
                allow_service=allow_service,
                id_type=UUID,
                denial=character_denial,
            )
        )
    ]


EDIT_CHARACTER = _character_permission("edit")
VIEW_CHARACTER = _character_permission("view")
EDIT_CHARACTER_OR_SERVICE = _character_permission("edit", allow_service=True)
VIEW_CHARACTER_OR_SERVICE = _character_permission("view", allow_service=True)


async def publish_character_event(event: Any) -> None:
    bus = get_event_bus()
    if bus:
        await publish_best_effort(bus, STREAM_CHARACTER, event)


async def publish_crafting_event(event: Any) -> None:
    bus = get_event_bus()
    if bus:
        await publish_best_effort(bus, STREAM_CRAFTING, event)


async def load_character(
    repo: AggregateRepository[CharacterAggregate], character_id: UUID
) -> CharacterAggregate:
    """Load the character. Only a missing stream is a 404. A store outage answers 503."""
    return await load_or_404(repo, character_id, f"Character not found: {character_id}")


async def create_new_character(
    repo: AggregateRepository[CharacterAggregate],
    req: CreateCharacterRequest,
    character_id: UUID,
) -> CharacterState:
    char = CharacterAggregate(character_id)
    char.create(
        name=req.name,
        character_class=req.character_class,
        max_hp=req.max_hp,
        level=req.level,
        portrait_url=req.portrait_url,
        player_id=req.player_id,
        personality_traits=req.personality_traits,
        campaign_id=req.campaign_id,
        subclass=req.subclass,
        armor_class=req.armor_class,
        speed_ft=req.speed_ft,
        ability_scores=req.ability_scores,
    )
    await repo.save(char)
    return char.state


async def execute_character_mutation(
    repo: AggregateRepository[CharacterAggregate],
    character_id: UUID,
    mutation_fn: Callable[[CharacterAggregate], Any],
) -> CharacterState:
    char = await load_character(repo, character_id)
    mutation_fn(char)
    await repo.save(char)
    return char.state


async def execute_condition_mutation(
    repo: AggregateRepository[CharacterAggregate],
    character_id: UUID,
    mutation_fn: Callable[[CharacterAggregate], Any],
) -> CharacterState:
    """Apply one condition change, save it, then publish the events it committed.

    The events are read before the save, because a save clears them. A refused change raises
    ValueError (HTTP 400 through the service handler) and publishes nothing.
    """
    char = await load_character(repo, character_id)
    mutation_fn(char)
    committed = list(char.uncommitted_events)
    await repo.save(char)
    for event in committed:
        await publish_character_event(event)
    return char.state


async def modify_character_health(
    repo: AggregateRepository[CharacterAggregate],
    character_id: UUID,
    delta: int,
    source: str,
    is_stand_in: bool | None,
    session_id: str | None = None,
) -> CharacterState:
    char = await load_character(repo, character_id)
    was_stabilized = char.state.is_stabilized
    char.modify_health(
        delta=delta, source=source, is_stand_in=is_stand_in, session_id=session_id or None
    )
    await repo.save(char)
    for event in health_change_events(
        character_id,
        char,
        delta=delta,
        source=source,
        session_id=session_id,
        was_stabilized=was_stabilized,
    ):
        await publish_character_event(event)
    return char.state


async def update_character_guardrails(
    repo: AggregateRepository[CharacterAggregate],
    character_id: UUID,
    req: StandInGuardrailPolicy,
) -> CharacterState:
    char = await load_character(repo, character_id)
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


async def assign_character_campaign(
    repo: AggregateRepository[CharacterAggregate],
    spicedb: SpiceDBClient | MockSpiceDBClient,
    character_id: UUID,
    campaign_id: str | None,
    assigned_by: str,
) -> CharacterState:
    """Validate the assignment, write the campaign tuple, then save the character.

    The tuple write comes before the save. A failed write leaves the character unchanged.
    """
    char = await load_character(repo, character_id)
    char.assign_campaign(campaign_id, assigned_by)
    await replace_character_campaign(spicedb, character_id, campaign_id)
    await repo.save(char)
    await publish_character_event(
        CharacterAssignedToCampaign(
            aggregate_id=character_id,
            character_id=str(character_id),
            campaign_id=campaign_id,
            assigned_by=assigned_by,
        )
    )
    return char.state
