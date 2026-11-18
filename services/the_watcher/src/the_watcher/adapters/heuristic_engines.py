"""Adapters that run The Watcher's local rule engine. Selected only by explicit setting.

The local engine never stands in for a failed worker. The narrator has no local engine, so it
raises `EngineUnavailableError` (HTTP 503) instead of returning text.
"""

from __future__ import annotations

from runefoble_platform.engine_ports import EngineUnavailableError
from the_watcher.models import (
    DMGuidanceRequest,
    DMNarrationResult,
    IntentResult,
    SpeechInputRequest,
    StandInAction,
    StandInRequest,
)
from the_watcher.ports import IntentParser, SceneNarrator, StandInDecider
from the_watcher.watcher_ai import TheWatcherEngine

HEURISTIC_ENGINE = "heuristic"


class HeuristicIntentParser(IntentParser):
    """Parses speech with the regex grammar of the local engine."""

    engine_name = HEURISTIC_ENGINE

    def __init__(self, engine: TheWatcherEngine) -> None:
        self._engine = engine

    async def parse(self, req: SpeechInputRequest) -> IntentResult:
        return self._engine.parse_speech_intent(req.transcript, req.speaker_name)


class HeuristicStandInDecider(StandInDecider):
    """Chooses stand-in actions with the template rules of the local engine."""

    engine_name = HEURISTIC_ENGINE

    def __init__(self, engine: TheWatcherEngine) -> None:
        self._engine = engine

    async def decide(self, req: StandInRequest) -> StandInAction:
        return self._engine.generate_stand_in_action(
            character_name=req.character_name,
            character_class=req.character_class,
            penalties=req.penalties,
            scene_context=req.scene_context,
            personality_traits=req.personality_traits,
            guardrails=req.guardrails,
        )


class HeuristicSceneNarrator(SceneNarrator):
    """Has no narration engine. Every call is an explicit 503."""

    engine_name = HEURISTIC_ENGINE

    async def narrate(self, req: DMGuidanceRequest) -> DMNarrationResult:
        raise EngineUnavailableError(
            "backend_unavailable",
            self.engine_name,
            "The heuristic engine has no scene narration. Set RUNEFOBLE_WATCHER_ENGINE to "
            "'inference_worker' and configure RUNEFOBLE_INFERENCE_URL.",
            engine_field="backend",
        )
