"""Campaign homebrew rule registration endpoints guarded by SpiceDB Zanzibar authorization."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from runefoble_auth.errors import AuthzWriteError
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.aggregate_loading import load_or_create
from runefoble_platform.event_sourcing import AggregateRepository

from rules_compendium.aggregate import CompendiumAggregate
from rules_compendium.dependencies import (
    CallerId,
    check_user_can_manage_homebrew,
    get_compendium_repo,
    get_principal,
    get_retrieval_engine,
    get_spicedb_client,
)
from rules_compendium.homebrew_access import campaign_homebrew_rules, visible_homebrew_rule_ids
from rules_compendium.models import HomebrewCreateRequest, HomebrewResponse
from rules_compendium.retrieval import CompendiumRetrievalEngine

router = APIRouter(
    prefix="/api/v1/compendium/homebrew",
    tags=["Homebrew Rules"],
    dependencies=[Depends(get_principal)],
)


@router.post("", response_model=HomebrewResponse)
async def register_homebrew_rule(
    request: HomebrewCreateRequest,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    compendium_repo: Annotated[
        AggregateRepository[CompendiumAggregate], Depends(get_compendium_repo)
    ],
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)],
) -> HomebrewResponse:
    """Register custom campaign homebrew monster or rule guarded by SpiceDB Zanzibar authorization."""
    # Check Zanzibar permission: user must have manage or run_session on the campaign
    can_manage = await check_user_can_manage_homebrew(user_id, request.campaign_id, spicedb)
    if not can_manage:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: User '{user_id}' does not have permission to register homebrew for campaign '{request.campaign_id}'",
        )

    rule_id = uuid4()

    # Zanzibar relationships first: a failed write must leave no saved rule behind.
    try:
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
    except AuthzWriteError as exc:
        raise HTTPException(status_code=503, detail="authorization_unavailable") from exc

    # Event sourcing via CompendiumAggregate
    compendium = await load_or_create(compendium_repo, request.campaign_id, CompendiumAggregate)
    compendium.register_homebrew(
        rule_id=rule_id,
        campaign_id=request.campaign_id,
        author_id=user_id,
        rule_type=request.rule_type,
        title=request.title,
        content=request.content,
    )
    await compendium_repo.save(compendium)

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
    user_id: CallerId,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)],
    compendium_repo: Annotated[
        AggregateRepository[CompendiumAggregate], Depends(get_compendium_repo)
    ],
) -> list[dict]:
    """Return the campaign homebrew rules that the caller may view (`homebrew_rule.view`).

    Rules come from the campaign aggregate. A rule whose name an SRD entry already has is
    listed with `shadowed: true`. The SRD entry still wins in lookup and search.
    """
    rules = await campaign_homebrew_rules(campaign_id, compendium_repo)
    visible_ids = await visible_homebrew_rule_ids(user_id, rules, spicedb)
    return [
        {**rule, "shadowed": engine.is_shadowed(rule["title"])}
        for rule in rules
        if str(rule["rule_id"]) in visible_ids
    ]
