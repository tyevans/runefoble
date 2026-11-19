"""Dependency injection and shared singletons for the Rules Compendium service."""

from uuid import UUID

from fastapi import Request
from runefoble_auth.factory import get_spicedb_client as get_spicedb_client
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_auth.permissions import check_subject
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.wiring import (
    build_identity_dependencies,
    make_verifier_holder,
    verifier_from_settings,
)
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.service_credential import expected_service_credential

from rules_compendium.aggregate import CompendiumAggregate, EncounterAggregate
from rules_compendium.retrieval import CompendiumRetrievalEngine

settings = PlatformSettings()

# Global singletons


def get_compendium_repo() -> AggregateRepository[CompendiumAggregate]:
    """Provide CompendiumAggregate repository on the process event store.

    The store is resolved per call, as the start-up projection does, so both read the same store.
    """
    return create_aggregate_repository(CompendiumAggregate)


def get_encounter_repo() -> AggregateRepository[EncounterAggregate]:
    """Provide EncounterAggregate repository."""
    return create_aggregate_repository(EncounterAggregate)


def get_retrieval_engine(request: Request) -> CompendiumRetrievalEngine:
    """Provide the retrieval engine owned by this application instance."""
    engine: CompendiumRetrievalEngine = request.app.state.retrieval_engine
    return engine


get_zitadel_auth_service, set_zitadel_auth_service = make_verifier_holder(
    lambda: verifier_from_settings(settings)
)
SERVICE_CREDENTIAL = expected_service_credential()
get_principal, CallerPrincipal, CallerId, get_caller_or_service, CallerOrService = (
    build_identity_dependencies(get_zitadel_auth_service, SERVICE_CREDENTIAL)
)


async def check_user_can_view_homebrew_rule(
    user_id: str,
    rule_id: str,
    spicedb: SpiceDBClient | MockSpiceDBClient,
) -> bool:
    """Check `homebrew_rule.view` (campaign viewers or the author) under the Zanzibar schema."""
    return await check_subject(spicedb, "homebrew_rule", rule_id, "view", user_id)


async def check_user_can_manage_homebrew(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBClient | MockSpiceDBClient,
) -> bool:
    """Check `campaign.manage` or `campaign.run_session` before a new homebrew rule is written."""
    for permission in ("manage", "run_session"):
        allowed = await check_subject(spicedb, "campaign", str(campaign_id), permission, user_id)
        if allowed:
            return True
    return False
