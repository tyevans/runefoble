"""Game Session Microservice - Powered by eventsource-py.

Coordinates active sessions, participant presence, turn order, and campaign timelines.
"""

import contextlib
import logging
import os
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, HTTPException
from game_session.aggregate import GameSessionAggregate, GameSessionState, ParticipantState
from game_session.combat_routes import (
    init_combat_routes,
)
from game_session.combat_routes import (
    router as combat_router,
)
from game_session.models import (
    AutoPilotRequest,
    AutoPilotResponse,
    CreateSessionRequest,
    JoinSessionRequest,
    LeaveSessionRequest,
    RollDiceRequest,
    RollDiceResponse,
)
from runefoble_events.events import (
    AbsencePenaltyApplied,
    DiceRolled,
    SessionStarted,
    StandInActionDecided,
)
from runefoble_platform.config import PlatformSettings
from runefoble_platform.dice import parse_and_roll
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
    get_event_store,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.watcher_ai import StandInAction, TheWatcherEngine

logger = logging.getLogger("runefoble.game_session")
WATCHER_SERVICE_URL = os.environ.get("RUNEFOBLE_WATCHER_URL")
STREAM_WATCHER = "runefoble.events.watcher"
STREAM_SESSION = "runefoble.events.session"

platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None


def get_event_bus() -> RedisStreamsEventBus | None:
    global _event_bus
    if _event_bus is None and platform_settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus


app = FastAPI(
    title="Runefoble - Game Session Service",
    version="0.1.0",
    description="Session Lifecycle, Turn / Initiative Order, and Live Participation backed by eventsource-py.",
)

# Global aggregate repository
repo: AggregateRepository[GameSessionAggregate] = create_aggregate_repository(GameSessionAggregate)
init_combat_routes(repo, get_event_bus)
app.include_router(combat_router)


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "game_session",
        "event_store": type(get_event_store()).__name__,
    }


@app.post("/api/v1/sessions/create", response_model=GameSessionState)
async def create_session(req: CreateSessionRequest):
    """Create a new event-sourced game session."""
    session_id = uuid4()
    session = GameSessionAggregate(session_id)
    session.create(campaign_id=req.campaign_id, title=req.title, dm_id=req.dm_id)
    await repo.save(session)
    return session.state


@app.get("/api/v1/sessions/{session_id}", response_model=GameSessionState)
async def get_session(session_id: UUID):
    """Load session state reconstituted from the event stream."""
    try:
        session = await repo.load(session_id)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e


@app.post("/api/v1/sessions/{session_id}/start", response_model=GameSessionState)
async def start_session(session_id: UUID):
    """Transition session from lobby to active."""
    try:
        session = await repo.load(session_id)
        session.start()
        await repo.save(session)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    bus = get_event_bus()
    if bus:
        with contextlib.suppress(Exception):
            await bus.publish_event(
                STREAM_SESSION,
                SessionStarted(
                    aggregate_id=session_id,
                    started_at_turn=session.state.current_turn,
                ),
            )

    return session.state


@app.post("/api/v1/sessions/{session_id}/join", response_model=GameSessionState)
async def join_session(session_id: UUID, req: JoinSessionRequest):
    """Record player entering session."""
    try:
        session = await repo.load(session_id)
        session.join_player(
            player_id=req.player_id,
            character_id=req.character_id,
            character_name=req.character_name,
            character_class=req.character_class,
        )
        await repo.save(session)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/sessions/{session_id}/leave", response_model=GameSessionState)
async def leave_session(session_id: UUID, req: LeaveSessionRequest):
    """Record player absence, marking character for AI stand-in."""
    try:
        session = await repo.load(session_id)
        session.leave_player(player_id=req.player_id, reason=req.reason)
        await repo.save(session)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/sessions/{session_id}/next-turn", response_model=GameSessionState)
async def advance_turn(session_id: UUID):
    """Advance to the next turn in the session."""
    try:
        session = await repo.load(session_id)
        session.advance_turn()
        await repo.save(session)
        return session.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/sessions/{session_id}/roll", response_model=RollDiceResponse)
async def roll_dice_session(
    session_id: UUID, req: RollDiceRequest | None = None
) -> RollDiceResponse:
    """Evaluate a dice roll, emit a DiceRolled domain event, and record to the session."""
    req_data = req or RollDiceRequest()
    result = parse_and_roll(req_data.formula)

    event = DiceRolled(
        aggregate_id=session_id,
        session_id=str(session_id),
        roller_id=req_data.roller_id,
        roller_name=req_data.roller_name,
        formula=req_data.formula,
        total=result["total"],
        rolls=result["rolls"],
        is_crit=result.get("is_crit", False),
        is_fumble=result.get("is_fumble", False),
    )

    bus = get_event_bus()
    if bus:
        with contextlib.suppress(Exception):
            await bus.publish_event(STREAM_SESSION, event)

    return RollDiceResponse(
        session_id=session_id,
        roller_id=req_data.roller_id,
        roller_name=req_data.roller_name,
        formula=req_data.formula,
        total=result["total"],
        rolls=result["rolls"],
        is_crit=result.get("is_crit", False),
        is_fumble=result.get("is_fumble", False),
        roll_type=req_data.roll_type,
    )


@app.post(
    "/api/v1/sessions/{session_id}/turns/auto-pilot",
    response_model=AutoPilotResponse,
)
async def auto_pilot_turn(
    session_id: UUID,
    req: AutoPilotRequest | None = None,
):
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
            detail=f"Character '{target_participant.character_name}' is not marked as absent (is_stand_in_active is False)",
        )

    # Invoke The Watcher stand-in engine
    stand_in_action: StandInAction | None = None
    if WATCHER_SERVICE_URL:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(
                    f"{WATCHER_SERVICE_URL}/api/v1/watcher/stand-in/act",
                    json={
                        "character_name": target_participant.character_name,
                        "character_class": target_participant.character_class,
                        "penalties": request_data.penalties,
                        "scene_context": request_data.scene_context,
                        "personality_traits": request_data.personality_traits,
                        "session_id": str(session_id),
                        "campaign_id": str(session.state.campaign_id),
                    },
                )
                if res.status_code == 200:
                    stand_in_action = StandInAction.model_validate(res.json())
        except Exception as e:
            logger.warning(
                "Failed to invoke remote watcher service: %s. Falling back to local engine.", e
            )

    if stand_in_action is None:
        engine = TheWatcherEngine()
        stand_in_action = engine.generate_stand_in_action(
            character_name=target_participant.character_name,
            character_class=target_participant.character_class,
            penalties=request_data.penalties,
            scene_context=request_data.scene_context,
            personality_traits=request_data.personality_traits,
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

    # Dispatch to Redis Streams
    bus = get_event_bus()
    if bus:
        try:
            action_event = StandInActionDecided(
                aggregate_id=session_id,
                session_id=session_id,
                campaign_id=session.state.campaign_id,
                character_name=stand_in_action.character_name,
                action_type=stand_in_action.action_type,
                dialogue=stand_in_action.dialogue,
                penalties_applied=stand_in_action.penalties_applied or request_data.penalties,
                flavor_text=stand_in_action.action_description,
            )
            await bus.publish_event(STREAM_WATCHER, action_event)
            for p in request_data.penalties:
                p_clean = p.lower()
                if p_clean in ("drunk", "foolishness", "cowardice", "greed", "curse"):
                    pen_event = AbsencePenaltyApplied(
                        aggregate_id=session_id,
                        session_id=session_id,
                        campaign_id=session.state.campaign_id,
                        penalty_type=p_clean,
                        description=stand_in_action.penalty_influence
                        or f"Absence penalty {p} active",
                        imposed_by="the_watcher",
                    )
                    await bus.publish_event(STREAM_WATCHER, pen_event)
        except Exception as e:
            logger.warning(
                "Failed to publish auto-pilot event to Redis stream '%s': %s", STREAM_WATCHER, e
            )

    return AutoPilotResponse(
        session_id=session_id,
        current_turn=session.state.current_turn,
        action=stand_in_action,
        stand_in_action=stand_in_action,
        session_state=session.state,
    )


@app.get("/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for game session."""
    return {
        "service": "game_session",
        "package": "@runefoble/game-session-ui",
        "components": [
            "runefoble-initiative-tracker",
            "runefoble-dice-roller",
            "runefoble-spectator-view",
        ],
        "version": "0.1.0",
    }


def main():
    import uvicorn

    uvicorn.run("game_session.main:app", host="0.0.0.0", port=8004, reload=True)


if __name__ == "__main__":
    main()
