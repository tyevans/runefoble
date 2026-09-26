"""The Watcher AI Microservice API."""

from fastapi import FastAPI
from pydantic import BaseModel, Field
from the_watcher.watcher_ai import IntentResult, StandInAction, TheWatcherEngine

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
    return {"status": "ok", "service": "the_watcher"}


@app.post("/api/v1/watcher/transcribe-and-act", response_model=IntentResult)
async def process_speech_action(req: SpeechInputRequest):
    """Parse player speech, translate to game action, and trigger board state update."""
    return engine.parse_speech_intent(req.transcript, req.speaker_name)


@app.post("/api/v1/watcher/stand-in/act", response_model=StandInAction)
async def stand_in_act(req: StandInRequest):
    """Simulate an action for an absent player's character with applied penalties."""
    return engine.generate_stand_in_action(
        character_name=req.character_name,
        character_class=req.character_class,
        penalties=req.penalties,
        scene_context=req.scene_context,
    )


@app.post("/api/v1/watcher/narrate")
async def narrate_scene(req: DMGuidanceRequest):
    """Autonomous DM scene description and event resolution."""
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
