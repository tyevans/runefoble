import logging
import os

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field
from the_watcher.watcher_ai import IntentResult, StandInAction, TheWatcherEngine

logger = logging.getLogger("runefoble.the_watcher")
INFERENCE_URL = os.environ.get("RUNEFOBLE_INFERENCE_URL")

app = FastAPI(
    title="Runefoble - The Watcher Service",
    version="0.1.0",
    description="AI Gameplay System: Speech-to-Intent, Board Animator, Autonomous DM & Missing Player Stand-in.",
)

engine = TheWatcherEngine()


class SpeechInputRequest(BaseModel):
    speaker_id: str
    speaker_name: str
    transcript: str
    session_id: str
    campaign_id: str


class StandInRequest(BaseModel):
    character_name: str
    character_class: str
    penalties: list[str] = Field(default_factory=list)
    scene_context: str = "In combat with subterranean creatures"


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
    """Parse player speech, translate to game action, and trigger board state update."""
    if INFERENCE_URL:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
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
                    return IntentResult(
                        action_type=action.get("action_type", "unknown"),
                        target=action.get("target_token_name"),
                        details=action.get("narrative_flavor", req.transcript),
                        confidence=action.get("confidence", 0.9),
                    )
        except Exception as e:
            logger.warning("Inference worker failed: %s. Falling back to local engine.", e)

    return engine.parse_speech_intent(req.transcript, req.speaker_name)


@app.post("/api/v1/watcher/stand-in/act", response_model=StandInAction)
async def stand_in_act(req: StandInRequest):
    """Simulate an action for an absent player's character with applied penalties."""
    if INFERENCE_URL:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{INFERENCE_URL}/inference/v1/stand-in-action",
                    json={
                        "campaign_id": "current-campaign",
                        "session_id": "current-session",
                        "character_name": req.character_name,
                        "character_class": req.character_class,
                        "penalties": req.penalties,
                        "scene_context": req.scene_context,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    return StandInAction(
                        character_name=data.get("character_name", req.character_name),
                        action_type=data.get("action_type", "attack"),
                        dialogue=data.get("dialogue", "..."),
                        penalties_applied=data.get("penalties_applied", req.penalties),
                        flavor_text=data.get("narrative_flavor", ""),
                    )
        except Exception as e:
            logger.warning("Inference worker failed: %s. Falling back to local engine.", e)

    return engine.generate_stand_in_action(
        character_name=req.character_name,
        character_class=req.character_class,
        penalties=req.penalties,
        scene_context=req.scene_context,
    )


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
