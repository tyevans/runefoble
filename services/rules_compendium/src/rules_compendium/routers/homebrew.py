"""Campaign homebrew rule registration endpoints guarded by SpiceDB Zanzibar authorization."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.event_sourcing import AggregateRepository

from rules_compendium.aggregate import CompendiumAggregate
from rules_compendium.dependencies import (
    check_user_can_manage_homebrew,
    check_user_can_view_campaign,
    get_compendium_repo,
    get_current_user_id,
    get_retrieval_engine,
    get_spicedb_client,
)
from rules_compendium.models import HomebrewCreateRequest, HomebrewResponse
from rules_compendium.retrieval import CompendiumRetrievalEngine

router = APIRouter(prefix="/api/v1/compendium/homebrew", tags=["Homebrew Rules"])


@router.post("", response_model=HomebrewResponse)
async def register_homebrew_rule(
    request: HomebrewCreateRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    compendium_repo: Annotated[
        AggregateRepository[CompendiumAggregate], Depends(get_compendium_repo)
    ],
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)],
) -> HomebrewResponse:
    """Register custom campaign homebrew monster or rule guarded by SpiceDB Zanzibar authorization."""
    # Check Zanzibar permission: user must have manage or run_session on the campaign
    if not user_id:
        raise HTTPException(
            status_code=401, detail="Authentication required to register homebrew rules"
        )

    can_manage = await check_user_can_manage_homebrew(user_id, request.campaign_id, spicedb)
    if not can_manage:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: User '{user_id}' does not have permission to register homebrew for campaign '{request.campaign_id}'",
        )

    rule_id = uuid4()

    # Event sourcing via CompendiumAggregate
    try:
        compendium = await compendium_repo.load(request.campaign_id)
    except Exception:
        compendium = CompendiumAggregate(request.campaign_id)
    compendium.register_homebrew(
        rule_id=rule_id,
        campaign_id=request.campaign_id,
        author_id=user_id,
        rule_type=request.rule_type,
        title=request.title,
        content=request.content,
    )
    await compendium_repo.save(compendium)

    # Establish Zanzibar relationship in SpiceDB: homebrew_rule bound to campaign and author
    await spicedb.write_relationship(
        resource_type="homebrew_rule",
        resource_id=str(rule_id),
        relation="campaign",
        subject_type="campaign",
        subject_id=str(request.campaign_id),
    )
    await spicedb.write_relationship(
        resource_type="homebrew_rule",
        resource_id=str(rule_id),
        relation="author",
        subject_type="user",
        subject_id=user_id,
    )

    # Index into redstring retrieval engine
    await engine.index_homebrew_rule(
        rule_id=rule_id,
        campaign_id=request.campaign_id,
        author_id=user_id,
        rule_type=request.rule_type,
        title=request.title,
        content=request.content,
    )

    return HomebrewResponse(
        rule_id=rule_id,
        campaign_id=request.campaign_id,
        author_id=user_id,
        rule_type=request.rule_type,
        title=request.title,
        content=request.content,
        status="registered",
    )


@router.get("/{campaign_id}")
async def list_campaign_homebrew(
    campaign_id: UUID,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)],
) -> list[dict]:
    """Retrieve all homebrew rules for a campaign under Zanzibar authorization."""
    can_view = await check_user_can_view_campaign(user_id, campaign_id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: User '{user_id}' cannot view homebrew for campaign '{campaign_id}'",
        )
    return engine.get_homebrew_by_campaign(campaign_id)
