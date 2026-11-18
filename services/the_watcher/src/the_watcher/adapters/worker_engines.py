"""Adapters that call the inference worker for The Watcher ports."""

from __future__ import annotations

from the_watcher.board_client import fetch_visible_tokens
from the_watcher.models import (
    DMGuidanceRequest,
    DMNarrationResult,
    IntentResult,
    SpeechInputRequest,
    StandInAction,
    StandInRequest,
)
from the_watcher.ports import IntentParser, SceneNarrator, StandInDecider
from the_watcher.worker_client import WORKER_ENGINE, call_worker


class WorkerIntentParser(IntentParser):
    """Parses speech with the worker. The worker receives the session's visible tokens."""

    engine_name = WORKER_ENGINE

    def __init__(self, base_url: str, board_state_url: str | None) -> None:
        self._base_url = base_url
        self._board_state_url = board_state_url

    async def parse(self, req: SpeechInputRequest) -> IntentResult:
        visible_tokens = await fetch_visible_tokens(self._board_state_url, req.session_id)
        data = await call_worker(
            self._base_url,
            "/inference/v1/intent",
            {
                "campaign_id": req.campaign_id,
                "session_id": req.session_id,
                "speaker_id": req.speaker_id,
                "speaker_name": req.speaker_name,
                "transcript": req.transcript,
                "visible_tokens": visible_tokens,
            },
            timeout=2.0,
        )
        action = data["action"]
        target_name = action.get("target_token_name") or action.get("target_token_id")
        return IntentResult(
            action_type=action["action_type"],
            confidence=action.get("confidence"),
            parameters=action,
            target=target_name,
            details=action.get("narrative_flavor", req.transcript),
            watcher_reply=action.get("narrative_flavor", ""),
            source=data["source"],
            degraded=data["degraded"],
        )


class WorkerStandInDecider(StandInDecider):
    """Chooses stand-in actions with the worker."""

    engine_name = WORKER_ENGINE

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def decide(self, req: StandInRequest) -> StandInAction:
        guardrails = req.guardrails.model_dump() if req.guardrails is not None else None
        data = await call_worker(
            self._base_url,
            "/inference/v1/stand-in-action",
            {
                "campaign_id": req.campaign_id,
                "session_id": req.session_id,
                "character_name": req.character_name,
                "character_class": req.character_class,
                "penalties": req.penalties,
                "scene_context": req.scene_context,
                "personality_traits": req.personality_traits,
                "guardrails": guardrails,
            },
            timeout=10.0,
        )
        return StandInAction(
            character_name=data["character_name"],
            action_type=data["action_type"],
            action_description=data["narrative_flavor"],
            dialogue=data["dialogue"],
            penalties_applied=data["penalties_applied"],
            guardrails_applied=data["guardrails_applied"],
            flavor_text=data["narrative_flavor"],
            source=data["source"],
            degraded=data["degraded"],
        )


class WorkerSceneNarrator(SceneNarrator):
    """Writes scene narration with the worker. There is no other narration engine."""

    engine_name = WORKER_ENGINE

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def narrate(self, req: DMGuidanceRequest) -> DMNarrationResult:
        data = await call_worker(
            self._base_url,
            "/inference/v1/dm-narration",
            {
                "campaign_id": req.campaign_id,
                "session_id": req.session_id,
                "scene_environment": req.scene_environment,
                "tone": req.tone,
                "guidance_prompt": req.prompt,
            },
            timeout=10.0,
        )
        return DMNarrationResult(
            session_id=req.session_id,
            narrative=data["narration"],
            sensory_details=data["sensory_details"],
            suggested_dm_prompts=data["suggested_dm_prompts"],
            tension_level=data["tension_level"],
            source=data["source"],
            degraded=data["degraded"],
        )
