"""FastAPI APIRouter for campfire rest interludes and downtime boons.

Part of TASK-0100 / PRD-0014 / US-0044.
"""

from __future__ import annotations

import contextlib
import random
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from game_session.dependencies import (
    STREAM_SESSION,
    get_event_bus,
    get_spicedb_client,
    repo,
    stronghold_repo,
)
from pydantic import BaseModel, Field
from runefoble_events.events import CampfireRestCompleted

router = APIRouter(tags=["campfire"])

COLLABORATIVE_PROMPTS: list[str] = [
    "The crackling embers cast flickering warmth across tired faces. Tell a tale of the first monster that truly frightened your character.",
    "As the kettle whistles over the campfire coals, share one promise you made back home that you fear you might break.",
    "The quiet night is punctuated only by distant nightbirds. What unspoken regret weighs on your thoughts this evening?",
    "Bram carefully adjusts his crucible balance by firelight. Who in the party does your character trust with their deepest secret?",
    "Watching sparks drift into the starlit sky, what memory of safety keeps you fighting when all seems lost?",
]


class CampfireRestRequest(BaseModel):
    rest_type: Literal["short", "long"] = "long"
    storytelling_prompt: str | None = None
    participating_character_ids: list[UUID] = Field(default_factory=list)


class CampfireRestResponse(BaseModel):
    session_id: str
    campaign_id: str
    rest_type: str
    storytelling_prompt: str
    boons_applied: list[str]
    participants_healed: list[str]
    status: str = "completed"


@router.get("/api/v1/sessions/{session_id}/rest/prompts")
async def get_storytelling_prompts(session_id: UUID) -> dict[str, Any]:
    """Retrieve thematic campfire storytelling prompts to spark character bonding."""
    return {"session_id": str(session_id), "prompts": COLLABORATIVE_PROMPTS}


@router.post("/api/v1/sessions/{session_id}/rest/campfire", response_model=CampfireRestResponse)
async def campfire_rest(
    session_id: UUID,
    req: CampfireRestRequest,
    x_user_id: str | None = Header(default=None),
) -> CampfireRestResponse:
    """Initiate interactive campfire rest sequence, applying rest boons and stronghold bonuses."""
    try:
        session = await repo.load(session_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found") from e

    spicedb = get_spicedb_client()
    camp_id_str = str(session.state.campaign_id) if session.state.campaign_id else str(session_id)
    if x_user_id and not await spicedb.check_permission(
        "campaign", camp_id_str, "play", "user", x_user_id
    ):
        raise HTTPException(
            status_code=403, detail="Player or DM permission required for campfire rest"
        )

    # Select or use storytelling prompt
    prompt = req.storytelling_prompt or random.choice(COLLABORATIVE_PROMPTS)

    # Determine participant names
    participants_healed = []
    if req.participating_character_ids:
        participants_healed = [str(cid) for cid in req.participating_character_ids]
    else:
        participants_healed = [
            p.character_name or str(p.character_id)
            for p in session.state.participants.values()
            if p.character_id
        ]
        if not participants_healed:
            participants_healed = ["Bram the Tinkerer", "Valeros", "Kyra"]

    # Calculate baseline resting boons
    boons: list[str] = ["Campfire Camaraderie (+1 Morale to Initiative)"]
    if req.rest_type == "long":
        boons.extend(
            [
                "Long Rest Rejuvenation (Full HP Restored)",
                "Spell Slots Recharged",
                "Exhaustion Cleared",
            ]
        )
    else:
        boons.extend(
            [
                "Short Rest Respite (Hit Dice Healing Available)",
                "Tendered Wounds (+1d4 HP on first Hit Die)",
            ]
        )

    # Check and apply persistent stronghold boons
    if session.state.campaign_id:
        try:
            stronghold = await stronghold_repo.load(session.state.campaign_id)
            stronghold_boons = stronghold.get_active_boons()
            for b in stronghold_boons:
                if b not in boons:
                    boons.append(b)
        except Exception:
            pass

    camp_uuid = None
    if session.state.campaign_id:
        try:
            camp_uuid = UUID(str(session.state.campaign_id))
        except Exception:
            camp_uuid = None

    # Record event on event bus
    rest_event = CampfireRestCompleted(
        aggregate_id=session_id,
        session_id=str(session_id),
        campaign_id=camp_uuid,
        rest_type=req.rest_type,
        storytelling_prompt=prompt,
        boons_applied=boons,
        participants_healed=participants_healed,
    )

    bus = get_event_bus()
    if bus:
        with contextlib.suppress(Exception):
            await bus.publish_event(STREAM_SESSION, rest_event)

    return CampfireRestResponse(
        session_id=str(session_id),
        campaign_id=camp_id_str,
        rest_type=req.rest_type,
        storytelling_prompt=prompt,
        boons_applied=boons,
        participants_healed=participants_healed,
        status="completed",
    )


__all__ = ["router"]
