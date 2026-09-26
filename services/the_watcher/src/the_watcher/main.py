import logging
import os
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field
from runefoble_events.events import (
    AbsencePenaltyApplied,
    SpeechIntentParsed,
    StandInActionDecided,
    TokenMoved,
    WatcherNarrationGenerated,
)
from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.watcher_ai import (
    IntentResult,
    StandInAction,
    StandInRecapResponse,
    TheWatcherEngine,
)

logger = logging.getLogger("runefoble.the_watcher")
INFERENCE_URL = os.environ.get("RUNEFOBLE_INFERENCE_URL")

STREAM_WATCHER = "runefoble.events.watcher"
STREAM_BOARD = "runefoble.events.board"

app = FastAPI(
    title="Runefoble - The Watcher Service",
    version="0.1.0",
    description="AI Gameplay System: Speech-to-Intent, Board Animator, Autonomous DM & Missing Player Stand-in.",
)

engine = TheWatcherEngine()
platform_settings = PlatformSettings()

_event_bus: RedisStreamsEventBus | None = None


def get_event_bus() -> RedisStreamsEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus


def to_uuid(val: str | UUID | None) -> UUID:
    """Deterministically convert a string or UUID into a valid UUID."""
    if val is None:
        return uuid4()
    if isinstance(val, UUID):
        return val
    try:
        return UUID(val)
    except ValueError:
        return uuid5(NAMESPACE_DNS, str(val))


class SpeechInputRequest(BaseModel):
    speaker_id: str
    speaker_name: str
    transcript: str
    session_id: str
    campaign_id: str
    token_id: str | None = None
    from_x: int | None = None
    from_y: int | None = None
    grid_cols: int = 12
    grid_rows: int = 12


class StandInRequest(BaseModel):
    character_name: str
    character_class: str
    penalties: list[str] = Field(default_factory=list)
    scene_context: str = "In combat with subterranean creatures"
    personality_traits: list[str] = Field(default_factory=list)
    session_id: str | None = None
    campaign_id: str | None = None


class StandInRecapRequest(BaseModel):
    character_name: str
    actions: list[Any] = Field(default_factory=list)
    penalties: list[str] = Field(default_factory=list)


class DMGuidanceRequest(BaseModel):
    session_id: str
    prompt: str


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "the_watcher",
        "inference_worker_url": INFERENCE_URL or "none (using local heuristic engine)",
    }


@app.post("/api/v1/watcher/transcribe-and-act", response_model=IntentResult)
async def process_speech_action(req: SpeechInputRequest):
    """Parse player speech, translate to game action, dispatch events, and trigger board state update."""
    intent: IntentResult | None = None

    if INFERENCE_URL:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post(
                    f"{INFERENCE_URL}/inference/v1/intent",
                    json={
                        "campaign_id": req.campaign_id,
                        "session_id": req.session_id,
                        "speaker_id": req.speaker_id,
                        "speaker_name": req.speaker_name,
                        "transcript": req.transcript,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    action = data.get("action", {})
                    target_name = action.get("target_token_name") or action.get("target_token_id")
                    intent = IntentResult(
                        action_type=action.get("action_type", "unknown"),
                        confidence=action.get("confidence", 0.9),
                        parameters=action,
                        target=target_name,
                        details=action.get("narrative_flavor", req.transcript),
                        watcher_reply=action.get("narrative_flavor")
                        or f"The Watcher acknowledges {req.speaker_name}.",
                    )
        except Exception as e:
            logger.warning("Inference worker failed: %s. Falling back to local engine.", e)

    if intent is None:
        intent = engine.parse_speech_intent(req.transcript, req.speaker_name)

    # Dispatch domain events across Redis Streams
    bus = get_event_bus()
    session_uuid = to_uuid(req.session_id)
    campaign_uuid = to_uuid(req.campaign_id)

    target_val = (
        intent.target or intent.parameters.get("target") or intent.parameters.get("target_token")
    )

    # 1. Dispatch SpeechIntentParsed to runefoble.events.watcher
    speech_intent_event = SpeechIntentParsed(
        aggregate_id=session_uuid,
        session_id=session_uuid,
        campaign_id=campaign_uuid,
        speaker_name=req.speaker_name,
        action_type=intent.action_type,
        target=target_val,
        confidence=intent.confidence,
        flavor_text=intent.watcher_reply,
        raw_transcript=req.transcript,
    )

    # 2. Dispatch WatcherNarrationGenerated to runefoble.events.watcher
    narration_event = WatcherNarrationGenerated(
        aggregate_id=session_uuid,
        session_id=session_uuid,
        campaign_id=campaign_uuid,
        narrative_text=intent.watcher_reply,
        tone="tactical" if intent.action_type in ("move", "attack") else "dark_fantasy",
    )

    try:
        await bus.publish_event(STREAM_WATCHER, speech_intent_event)
        await bus.publish_event(STREAM_WATCHER, narration_event)
    except Exception as e:
        logger.warning(
            "Failed to publish watcher events to Redis stream '%s': %s", STREAM_WATCHER, e
        )

    # 3. If action is movement, dispatch TokenMoved to runefoble.events.board
    if intent.action_type == "move":
        from_x = req.from_x if req.from_x is not None else 0
        from_y = req.from_y if req.from_y is not None else 0

        if "to_x" in intent.parameters and "to_y" in intent.parameters:
            to_x = int(intent.parameters["to_x"])
            to_y = int(intent.parameters["to_y"])
        else:
            dx = intent.parameters.get("dx", 0)
            dy = intent.parameters.get("dy", 0)
            to_x, to_y = engine.calculate_bounded_destination(
                from_x, from_y, dx, dy, cols=req.grid_cols, rows=req.grid_rows
            )

        token_id = req.token_id or f"token-{req.speaker_name.lower().replace(' ', '-')}"
        token_moved_event = TokenMoved(
            aggregate_id=session_uuid,
            session_id=session_uuid,
            campaign_id=campaign_uuid,
            token_id=token_id,
            name=req.speaker_name,
            from_x=from_x,
            from_y=from_y,
            to_x=to_x,
            to_y=to_y,
            initiated_by="player",
        )
        try:
            await bus.publish_event(STREAM_BOARD, token_moved_event)
        except Exception as e:
            logger.warning(
                "Failed to publish TokenMoved event to Redis stream '%s': %s", STREAM_BOARD, e
            )

    return intent


@app.post("/api/v1/watcher/stand-in/act", response_model=StandInAction)
async def stand_in_act(req: StandInRequest):
    """Simulate an action for an absent player's character with applied penalties."""
    stand_in: StandInAction | None = None
    if INFERENCE_URL:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{INFERENCE_URL}/inference/v1/stand-in-action",
                    json={
                        "campaign_id": req.campaign_id or "current-campaign",
                        "session_id": req.session_id or "current-session",
                        "character_name": req.character_name,
                        "character_class": req.character_class,
                        "penalties": req.penalties,
                        "scene_context": req.scene_context,
                        "personality_traits": req.personality_traits,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    stand_in = StandInAction(
                        character_name=data.get("character_name", req.character_name),
                        action_type=data.get("action_type", "attack"),
                        action_description=data.get("narrative_flavor", ""),
                        dialogue=data.get("dialogue", "..."),
                        penalties_applied=data.get("penalties_applied", req.penalties),
                        flavor_text=data.get("narrative_flavor", ""),
                    )
        except Exception as e:
            logger.warning("Inference worker failed: %s. Falling back to local engine.", e)

    if stand_in is None:
        stand_in = engine.generate_stand_in_action(
            character_name=req.character_name,
            character_class=req.character_class,
            penalties=req.penalties,
            scene_context=req.scene_context,
            personality_traits=req.personality_traits,
        )

    # Publish events to Redis Streams
    bus = get_event_bus()
    session_uuid = to_uuid(req.session_id)
    campaign_uuid = to_uuid(req.campaign_id) if req.campaign_id else None

    action_event = StandInActionDecided(
        aggregate_id=session_uuid,
        session_id=session_uuid,
        campaign_id=campaign_uuid,
        character_name=stand_in.character_name,
        action_type=stand_in.action_type,
        dialogue=stand_in.dialogue,
        penalties_applied=stand_in.penalties_applied or req.penalties,
        flavor_text=stand_in.action_description,
    )

    try:
        await bus.publish_event(STREAM_WATCHER, action_event)
        for p in req.penalties:
            p_clean = p.lower()
            if p_clean in ("drunk", "foolishness", "cowardice", "greed", "curse"):
                pen_event = AbsencePenaltyApplied(
                    aggregate_id=session_uuid,
                    session_id=session_uuid,
                    campaign_id=campaign_uuid,
                    penalty_type=p_clean,
                    description=stand_in.penalty_influence or f"Absence penalty {p} active",
                    imposed_by="the_watcher",
                )
                await bus.publish_event(STREAM_WATCHER, pen_event)
    except Exception as e:
        logger.warning(
            "Failed to publish stand-in events to Redis stream '%s': %s", STREAM_WATCHER, e
        )

    return stand_in


@app.post("/api/v1/watcher/stand-in/recap", response_model=StandInRecapResponse)
async def stand_in_recap(req: StandInRecapRequest):
    """Generate a humorous recap of an absent player's stand-in exploits for when they return."""
    data = engine.generate_stand_in_recap(
        character_name=req.character_name,
        actions=req.actions,
        penalties=req.penalties,
    )
    return StandInRecapResponse.model_validate(data)


@app.post("/api/v1/watcher/narrate")
async def narrate_scene(req: DMGuidanceRequest):
    """Autonomous DM scene description and event resolution."""
    if INFERENCE_URL:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{INFERENCE_URL}/inference/v1/dm-narration",
                    json={
                        "campaign_id": "current-campaign",
                        "session_id": req.session_id,
                        "scene_environment": "Dungeon chamber",
                        "tone": "dark_fantasy",
                        "guidance_prompt": req.prompt,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "session_id": req.session_id,
                        "narrative": data.get("narration"),
                        "sensory_details": data.get("sensory_details", []),
                        "suggested_dm_prompts": data.get("suggested_dm_prompts", []),
                        "tension_level": data.get("tension_level", "rising"),
                    }
        except Exception as e:
            logger.warning("Inference worker failed: %s. Falling back to local engine.", e)

    return {
        "session_id": req.session_id,
        "narrative": f"The shadows lengthen. {req.prompt}. An ominous chill fills the chamber as fate shifts.",
        "tone": "suspenseful",
    }


def main():
    import uvicorn

    uvicorn.run("the_watcher.main:app", host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    main()
