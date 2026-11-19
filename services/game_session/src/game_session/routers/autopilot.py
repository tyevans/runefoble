"""Auto-pilot stand-in turn execution routes for Game Session service."""

from __future__ import annotations

import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from game_session.aggregate import ParticipantState
from game_session.character_client import CharacterSheetUnavailableError, fetch_stand_in_policy
from game_session.container import watcher_service_url
from game_session.models import AutoPilotRequest, AutoPilotResponse
from game_session.play.repositories import SessionRepo
from game_session.routers.session_auth import session_permission
from game_session.shared.container_access import EventBus
from game_session.shared.streams import STREAM_WATCHER
from runefoble_events.events import AbsencePenaltyApplied
from runefoble_platform.event_publish import publish_aggregate_events
from runefoble_platform.stand_in_action import StandInAction

logger = logging.getLogger("runefoble.game_session")

router = APIRouter(dependencies=[Depends(session_permission("control"))], tags=["autopilot"])


async def _request_stand_in_action(watcher_url: str, payload: dict[str, object]) -> StandInAction:
    """Ask The Watcher for a stand-in action. Raise 503 when the call does not succeed."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(f"{watcher_url}/api/v1/watcher/stand-in/act", json=payload)
    except httpx.HTTPError as exc:
        logger.error("Auto-pilot: The Watcher at %s is unreachable: %s", watcher_url, exc)
        raise HTTPException(
            status_code=503,
            detail="The Watcher service is unreachable. No stand-in action was recorded.",
        ) from exc
    if res.status_code != 200:
        logger.error("Auto-pilot: The Watcher returned HTTP %s.", res.status_code)
        raise HTTPException(
            status_code=503,
            detail=(
                f"The Watcher service returned HTTP {res.status_code}. "
                "No stand-in action was recorded."
            ),
        )
    try:
        return StandInAction.model_validate(res.json())
    except ValueError as exc:
        logger.error("Auto-pilot: The Watcher returned an invalid stand-in action: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="The Watcher service returned an invalid stand-in action. Nothing was recorded.",
        ) from exc


@router.post(
    "/api/v1/sessions/{session_id}/turns/auto-pilot",
    response_model=AutoPilotResponse,
)
async def auto_pilot_turn(
    session_id: UUID,
    repo: SessionRepo,
    events: EventBus,
    req: AutoPilotRequest | None = None,
) -> AutoPilotResponse:
    """Automatically execute a turn for an absent character using The Watcher stand-in engine."""
    request_data = req or AutoPilotRequest()
    try:
        session = await repo.load(session_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e

    if session.state.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot take auto-pilot turn in session status '{session.state.status}'",
        )

    # Determine active participant
    target_participant: ParticipantState | None = None
    target_char_id = request_data.active_character_id or session.state.active_character_id

    if target_char_id:
        for p in session.state.participants.values():
            if p.character_id == target_char_id:
                target_participant = p
                break

    if target_participant is None and session.state.participants:
        part_list = list(session.state.participants.values())
        turn_idx = (session.state.current_turn - 1) % len(part_list)
        target_participant = part_list[turn_idx]

    if target_participant is None:
        raise HTTPException(status_code=400, detail="No active participant found for turn")

    # Check absent status
    if not target_participant.is_stand_in_active:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Character '{target_participant.character_name}' is not marked as absent "
                "(is_stand_in_active is False)"
            ),
        )

    # The Watcher is the only stand-in engine. A missing or failing Watcher stops the turn.
    watcher_url = watcher_service_url()
    if watcher_url is None:
        logger.error("Auto-pilot refused: RUNEFOBLE_WATCHER_URL is not set.")
        raise HTTPException(
            status_code=503,
            detail="The Watcher service is not configured (RUNEFOBLE_WATCHER_URL is unset).",
        )
    # The stored policy of the absent character is the only policy the stand-in obeys.
    try:
        policy = await fetch_stand_in_policy(target_participant.character_id)
    except CharacterSheetUnavailableError as e:
        logger.error("Auto-pilot refused: stored stand-in policy unavailable: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"The stored stand-in policy is unavailable. No stand-in action was recorded. {e}",
        ) from e

    stand_in_action = await _request_stand_in_action(
        watcher_url,
        {
            "character_name": target_participant.character_name,
            "character_class": target_participant.character_class,
            "penalties": request_data.penalties,
            "scene_context": request_data.scene_context,
            "personality_traits": request_data.personality_traits,
            "guardrails": policy.model_dump(mode="json"),
            "session_id": str(session_id),
            "campaign_id": str(session.state.campaign_id),
        },
    )

    # Record stand-in action on session aggregate & advance turn
    session.record_stand_in_action(
        character_name=stand_in_action.character_name,
        action_type=stand_in_action.action_type,
        dialogue=stand_in_action.dialogue,
        penalties_applied=stand_in_action.penalties_applied or request_data.penalties,
        flavor_text=stand_in_action.action_description,
    )
    session.advance_turn()
    await repo.save(session)

    # Dispatch absence penalties to Redis Streams. The stand-in action is published
    # by the session repository when it commits the aggregate above.
    bus = events.get()
    if bus:
        penalty_events = [
            AbsencePenaltyApplied(
                aggregate_id=session_id,
                session_id=session_id,
                campaign_id=session.state.campaign_id,
                penalty_type=p.lower(),
                description=(stand_in_action.penalty_influence or f"Absence penalty {p} active"),
                imposed_by="the_watcher",
            )
            for p in request_data.penalties
            if p.lower() in ("drunk", "foolishness", "cowardice", "greed", "curse")
        ]
        await publish_aggregate_events(bus, STREAM_WATCHER, penalty_events)

    return AutoPilotResponse(
        session_id=session_id,
        current_turn=session.state.current_turn,
        action=stand_in_action,
        stand_in_action=stand_in_action,
        session_state=session.state,
    )
