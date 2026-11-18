"""Dependency injection and shared singletons for the Rules Compendium service."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from runefoble_auth.caller import CallerIdentity, require_user_or_service_credential
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
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
_compendium_repo: AggregateRepository[CompendiumAggregate] = create_aggregate_repository(
    CompendiumAggregate
)
_encounter_repo: AggregateRepository[EncounterAggregate] = create_aggregate_repository(
    EncounterAggregate
)
_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None
_zitadel_auth_service: ZitadelAuthService | None = None


def get_compendium_repo() -> AggregateRepository[CompendiumAggregate]:
    """Provide CompendiumAggregate repository."""
    return _compendium_repo


def get_encounter_repo() -> AggregateRepository[EncounterAggregate]:
    """Provide EncounterAggregate repository."""
    return _encounter_repo


def get_retrieval_engine(request: Request) -> CompendiumRetrievalEngine:
    """Provide the retrieval engine owned by this application instance."""
    engine: CompendiumRetrievalEngine = request.app.state.retrieval_engine
    return engine


def get_spicedb_client() -> SpiceDBClient | MockSpiceDBClient:
    """Provide SpiceDB Zanzibar client."""
    global _spicedb_client
    if _spicedb_client is None:
        _spicedb_client = SpiceDBClient(
            endpoint=settings.spicedb_endpoint or "localhost:50051",
            token=settings.spicedb_preshared_key,
        )
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    """Override SpiceDB client for testing."""
    global _spicedb_client
    _spicedb_client = client


def get_zitadel_auth_service() -> ZitadelAuthService:
    """Provide the Zitadel verifier that this service trusts, built from platform settings."""
    global _zitadel_auth_service
    if _zitadel_auth_service is None:
        _zitadel_auth_service = ZitadelAuthService(
            issuer=settings.zitadel_issuer,
            audience=settings.zitadel_audience,
            internal_url=settings.zitadel_internal_url,
        )
    return _zitadel_auth_service


def set_zitadel_auth_service(service: ZitadelAuthService | None) -> None:
    """Override the Zitadel verifier for tests."""
    global _zitadel_auth_service
    _zitadel_auth_service = service


get_current_principal = require_principal(get_zitadel_auth_service)


# Service credential (ADR-0015 e). Read once at import, so a service without it never starts.
SERVICE_CREDENTIAL = expected_service_credential()
get_caller_or_service = require_user_or_service_credential(
    get_zitadel_auth_service, SERVICE_CREDENTIAL
)
CallerOrService = Annotated[CallerIdentity, Depends(get_caller_or_service)]


def get_current_user_id(
    principal: Annotated[VerifiedPrincipal, Depends(get_current_principal)],
) -> str:
    """Return the subject of the verified bearer token. Raise 401 when no token verifies."""
    return principal.user_id


async def check_user_can_view_campaign(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBClient | MockSpiceDBClient,
) -> bool:
    """Check if user can view campaign resources under Zanzibar schema."""
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="view",
        subject_type="user",
        subject_id=user_id,
    )


async def check_user_can_manage_homebrew(
    user_id: str,
    campaign_id: UUID,
    spicedb: SpiceDBClient | MockSpiceDBClient,
) -> bool:
    """Check if user can manage/register homebrew rules under Zanzibar schema."""
    # Check if user has manage or run_session on campaign
    can_run = await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="run_session",
        subject_type="user",
        subject_id=user_id,
    )
    if can_run:
        return True
    return await spicedb.check_permission(
        resource_type="campaign",
        resource_id=str(campaign_id),
        permission="manage",
        subject_type="user",
        subject_id=user_id,
    )


CurrentUserId = Annotated[str, Depends(get_current_user_id)]
