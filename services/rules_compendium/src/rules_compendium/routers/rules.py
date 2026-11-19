"""Rules compendium lookup and hybrid search endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from runefoble_auth.port import SpiceDBPort
from runefoble_platform.event_sourcing import AggregateRepository

from rules_compendium.aggregate import CompendiumAggregate
from rules_compendium.dependencies import (
    CallerId,
    CallerOrService,
    get_compendium_repo,
    get_principal,
    get_retrieval_engine,
    get_spicedb_client,
)
from rules_compendium.homebrew_access import (
    campaign_homebrew_rules,
    visible_homebrew_monster,
    visible_homebrew_rule_ids,
)
from rules_compendium.models import RuleSearchResponse
from rules_compendium.retrieval import CompendiumRetrievalEngine

router = APIRouter(
    prefix="/api/v1/compendium",
    tags=["Rules Compendium"],
)


@router.get(
    "/rules/search", dependencies=[Depends(get_principal)], response_model=RuleSearchResponse
)
async def search_rules(
    query: Annotated[
        str, Query(description="Search term (e.g. 'fire damage', 'paralyzed', 'goblin')")
    ],
    user_id: CallerId,
    category: Annotated[
        str | None, Query(description="Filter category ('monster', 'spell', 'condition')")
    ] = None,
    campaign_id: Annotated[UUID | None, Query(description="Campaign context for homebrew")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)] = None,
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)] = None,
    compendium_repo: Annotated[
        AggregateRepository[CompendiumAggregate], Depends(get_compendium_repo)
    ] = None,
) -> RuleSearchResponse:
    """Sub-50ms hybrid BM25 and vector search across canonical SRD and authorized homebrew rules."""
    visible_ids: frozenset[str] = frozenset()
    if campaign_id:
        rules = await campaign_homebrew_rules(campaign_id, compendium_repo)
        visible_ids = await visible_homebrew_rule_ids(user_id, rules, spicedb)

    results, took_ms = await engine.hybrid_search(
        query=query,
        category=category,
        campaign_id=campaign_id,
        visible_homebrew_ids=visible_ids,
        limit=limit,
    )

    return RuleSearchResponse(
        query=query,
        results_count=len(results),
        took_ms=took_ms,
        retrieval_mode=engine.retrieval_mode,
        results=results,
    )


@router.get("/monsters/{name}")
async def get_monster_by_name(
    name: str,
    caller: CallerOrService,
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)],
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)],
    campaign_id: Annotated[
        UUID | None, Query(description="Campaign whose homebrew monsters may be read")
    ] = None,
) -> dict:
    """Retrieve a monster stat block by name. SRD monsters are readable by any verified caller.

    A homebrew monster needs `campaign_id` and `homebrew_rule.view`. Otherwise it returns 404.
    """
    monster = engine.get_monster(name)
    if monster is None and campaign_id is not None and caller.user_id is not None:
        monster = await visible_homebrew_monster(caller.user_id, campaign_id, name, engine, spicedb)
    if not monster:
        raise HTTPException(status_code=404, detail=f"Monster '{name}' not found in compendium")
    return monster


@router.get("/spells/{name}", dependencies=[Depends(get_principal)])
async def get_spell_by_name(
    name: str,
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)],
) -> dict:
    """Retrieve full spell definition by name."""
    spell = engine.get_spell(name)
    if not spell:
        raise HTTPException(status_code=404, detail=f"Spell '{name}' not found in compendium")
    return spell


@router.get("/conditions/{name}", dependencies=[Depends(get_principal)])
async def get_condition_by_name(
    name: str,
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)],
) -> dict:
    """Retrieve condition mechanics by name."""
    condition = engine.get_condition(name)
    if not condition:
        raise HTTPException(status_code=404, detail=f"Condition '{name}' not found in compendium")
    return condition
