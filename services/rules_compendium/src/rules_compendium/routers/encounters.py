"""Automated CR encounter balancing router."""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from runefoble_platform.event_sourcing import AggregateRepository

from rules_compendium.aggregate import EncounterAggregate
from rules_compendium.dependencies import (
    get_encounter_repo,
    get_retrieval_engine,
)
from rules_compendium.encounter_builder import (
    build_balanced_encounter,
    calculate_party_thresholds,
)
from rules_compendium.models import (
    EncounterBalanceRequest,
    EncounterBalanceResponse,
)
from rules_compendium.retrieval import CompendiumRetrievalEngine

router = APIRouter(prefix="/api/v1/compendium/encounters", tags=["Encounter Builder"])


@router.post("/balance", response_model=EncounterBalanceResponse)
async def balance_encounter(
    request: EncounterBalanceRequest,
    encounter_repo: Annotated[AggregateRepository[EncounterAggregate], Depends(get_encounter_repo)],
    engine: Annotated[CompendiumRetrievalEngine, Depends(get_retrieval_engine)],
) -> EncounterBalanceResponse:
    """Calculate encounter lethality and recommend a synergistic monster group for a given party roster."""
    # Ensure SRD data is initialized
    await engine.initialize_srd_data()

    # Calculate party thresholds
    thresholds = calculate_party_thresholds(request.party_levels)

    # Build synergistic encounter
    monsters, total_raw_xp, multiplier, adjusted_xp, calculated_tier = build_balanced_encounter(
        party_levels=request.party_levels,
        target_difficulty=request.target_difficulty,
        desired_roles=request.desired_roles,
    )

    encounter_id = uuid4()
    total_monster_count = sum(m.count for m in monsters)

    # Event sourcing via EncounterAggregate
    encounter = EncounterAggregate(encounter_id)
    encounter.record_balanced_encounter(
        encounter_id=encounter_id,
        party_levels=request.party_levels,
        target_difficulty=request.target_difficulty,
        total_party_xp_threshold=thresholds,
        selected_monsters=[m.model_dump() for m in monsters],
        total_xp=total_raw_xp,
        adjusted_xp=adjusted_xp,
        difficulty_tier=calculated_tier,
        multiplier=multiplier,
        campaign_id=request.campaign_id,
    )
    await encounter_repo.save(encounter)

    # Generate tactical narrative summary
    roles_present = {m.role for m in monsters}
    tactical_summary = (
        f"Balanced {calculated_tier} encounter ({adjusted_xp} adjusted XP, {multiplier}x multiplier) "
        f"featuring {total_monster_count} combatants with tactical synergy across {', '.join(sorted(roles_present))}."
    )

    return EncounterBalanceResponse(
        encounter_id=encounter_id,
        party_levels=request.party_levels,
        party_size=len(request.party_levels),
        target_difficulty=request.target_difficulty,
        difficulty_tier=calculated_tier,
        total_party_xp_threshold=thresholds,
        monsters=monsters,
        total_monster_count=total_monster_count,
        total_raw_xp=total_raw_xp,
        multiplier=multiplier,
        adjusted_xp=adjusted_xp,
        tactical_summary=tactical_summary,
    )
