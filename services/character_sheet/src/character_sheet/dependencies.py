"""Shared dependencies, aggregate repository, and event bus for Character Sheet microservice."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Any
from uuid import UUID

from character_sheet.aggregate import CharacterAggregate
from character_sheet.authz import (
    authorize_character,
    replace_character_campaign,
)
from character_sheet.crafting import CraftingAggregate
from character_sheet.health_events import health_change_events
from character_sheet.models import CharacterState
from character_sheet.schemas import CreateCharacterRequest
from eventsource.domain.exceptions import AggregateNotFoundError
from fastapi import Depends, HTTPException
from runefoble_auth.caller import CallerIdentity, require_user_or_service_credential
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_events.events import (
    CharacterAssignedToCampaign,
    StandInPolicyUpdated,
)
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

_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None
_zitadel_auth_service: ZitadelAuthService | None = None

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


def get_spicedb_client() -> SpiceDBClient | MockSpiceDBClient:
    global _spicedb_client
    if _spicedb_client is None:
        _spicedb_client = SpiceDBClient()
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    global _spicedb_client
    _spicedb_client = client


RepoDep = Annotated[AggregateRepository[CharacterAggregate], Depends(get_repository)]
CraftingRepoDep = Annotated[
    AggregateRepository[CraftingAggregate], Depends(get_crafting_repository)
]
SpiceDep = Annotated[SpiceDBClient | MockSpiceDBClient, Depends(get_spicedb_client)]


def get_zitadel_auth_service() -> ZitadelAuthService:
    """Provide the Zitadel verifier built from platform settings (ADR-0015 (c))."""
    global _zitadel_auth_service
    if _zitadel_auth_service is None:
        _zitadel_auth_service = ZitadelAuthService(
            issuer=platform_settings.zitadel_issuer,
            audience=platform_settings.zitadel_audience,
            internal_url=platform_settings.zitadel_internal_url,
        )
    return _zitadel_auth_service


def set_zitadel_auth_service(service: ZitadelAuthService | None) -> None:
    """Override the Zitadel verifier for tests."""
    global _zitadel_auth_service
    _zitadel_auth_service = service


get_principal = require_principal(get_zitadel_auth_service)


# Service credential (ADR-0015 e). Read once at import, so a service without it never starts.
SERVICE_CREDENTIAL = expected_service_credential()
get_caller_or_service = require_user_or_service_credential(
    get_zitadel_auth_service, SERVICE_CREDENTIAL
)
CallerOrService = Annotated[CallerIdentity, Depends(get_caller_or_service)]


def verified_user_id(principal: Annotated[VerifiedPrincipal, Depends(get_principal)]) -> str:
    """Project the verified token subject. Every route in this service requires it."""
    return principal.user_id


VerifiedUserId = Annotated[str, Depends(verified_user_id)]


def require_character_permission(
    permission: str, *, allow_service: bool = False
) -> Callable[..., Awaitable[None]]:
    """Build a route dependency that checks one schema permission on the path's character.

    The check runs on every call. A user bearer needs the permission (403 otherwise). With
    `allow_service`, the service credential passes without a user. A missing or bad
    credential is a 401. The check fails closed when SpiceDB cannot answer (503).
    """

    async def _check_user(
        character_id: UUID,
        principal: Annotated[VerifiedPrincipal, Depends(get_principal)],
        spicedb: SpiceDep,
    ) -> None:
        await authorize_character(spicedb, character_id, permission, principal.user_id)

    async def _check_caller(
        character_id: UUID,
        caller: CallerOrService,
        spicedb: SpiceDep,
    ) -> None:
        if caller.user_id is not None:
            await authorize_character(spicedb, character_id, permission, caller.user_id)

    return _check_caller if allow_service else _check_user


EDIT_CHARACTER = [Depends(require_character_permission("edit"))]
VIEW_CHARACTER = [Depends(require_character_permission("view"))]
EDIT_CHARACTER_OR_SERVICE = [Depends(require_character_permission("edit", allow_service=True))]
VIEW_CHARACTER_OR_SERVICE = [Depends(require_character_permission("view", allow_service=True))]


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
    try:
        return await repo.load(character_id)
    except AggregateNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Character not found: {e}") from e


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
    try:
        mutation_fn(char)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await repo.save(char)
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
    try:
        char.assign_campaign(campaign_id, assigned_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
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
