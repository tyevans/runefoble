"""Rules compendium lookup and hybrid search endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from runefoble_auth.spicedb import SpiceDBClient

from rules_compendium.dependencies import (
    check_user_can_view_campaign,
    get_current_user_id,
    get_retrieval_engine,
    get_spicedb_client,
)
from rules_compendium.models import RuleSearchResponse
from rules_compendium.retrieval import CompendiumRetrievalEngine

router = APIRouter(prefix="/api/v1/compendium", tags=["Rules Compendium"])


@router.get("/rules/search", response_model=RuleSearchResponse)
async def search_rules(
    query: Annotated[
        str, Query(description="Search term (e.g. 'fire damage', 'paralyzed', 'goblin')")
    ],
    category: Annotated[
        str | None, Query(description="Filter category ('monster', 'spell', 'condition')")
    ] = None,
    campaign_id: Annotated[UUID | None, Query(description="Campaign context for homebrew")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)] = None,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)] = None,
) -> RuleSearchResponse:
    """Sub-50ms hybrid BM25 and vector search across canonical SRD and authorized homebrew rules."""
    can_view_homebrew = False
    if campaign_id:
        can_view_homebrew = await check_user_can_view_campaign(user_id, campaign_id, spicedb)

    results, took_ms = await engine.hybrid_search(
        query=query,
        category=category,
        campaign_id=campaign_id,
        can_view_homebrew=can_view_homebrew,
        limit=limit,
    )

    return RuleSearchResponse(
        query=query,
        results_count=len(results),
        took_ms=took_ms,
        results=results,
    )


@router.get("/monsters/{name}")
async def get_monster_by_name(
    name: str,
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)],
) -> dict:
    """Retrieve full monster stat block by name."""
    monster = engine.get_monster(name)
    if not monster:
        raise HTTPException(status_code=404, detail=f"Monster '{name}' not found in compendium")
    return monster


@router.get("/spells/{name}")
async def get_spell_by_name(
    name: str,
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)],
) -> dict:
    """Retrieve full spell definition by name."""
    spell = engine.get_spell(name)
    if not spell:
        raise HTTPException(status_code=404, detail=f"Spell '{name}' not found in compendium")
    return spell


@router.get("/conditions/{name}")
async def get_condition_by_name(
    name: str,
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)],
) -> dict:
    """Retrieve condition mechanics by name."""
    condition = engine.get_condition(name)
    if not condition:
        raise HTTPException(status_code=404, detail=f"Condition '{name}' not found in compendium")
    return condition
