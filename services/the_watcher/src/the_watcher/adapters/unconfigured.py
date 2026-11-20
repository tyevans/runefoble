"""Ports whose setting is `none`. They have no engine, so every call is an explicit 503.

An unconfigured port never returns text. The error names the setting that selects the engine.
"""

from __future__ import annotations

from runefoble_platform.engine_ports import EngineUnavailableError
from runefoble_platform.stand_in_action import StandInAction
from the_watcher.models import DMGuidanceRequest, DMNarrationResult, StandInRequest
from the_watcher.ports import SceneNarrator, StandInDecider

NONE_ENGINE = "none"


def _not_configured(port: str, setting: str) -> EngineUnavailableError:
    return EngineUnavailableError(
        "backend_unavailable",
        NONE_ENGINE,
        f"The {port} engine is not configured. Set {setting} to 'inference_worker' "
        "and configure RUNEFOBLE_INFERENCE_URL.",
        engine_field="backend",
    )


class UnconfiguredStandInDecider(StandInDecider):
    """The stand-in port has no engine."""

    engine_name = NONE_ENGINE

    async def decide(self, req: StandInRequest) -> StandInAction:
        raise _not_configured("stand-in", "RUNEFOBLE_WATCHER_STAND_IN_ENGINE")


class UnconfiguredSceneNarrator(SceneNarrator):
    """The narration port has no engine."""

    engine_name = NONE_ENGINE

    async def narrate(self, req: DMGuidanceRequest) -> DMNarrationResult:
        raise _not_configured("narration", "RUNEFOBLE_WATCHER_NARRATION_ENGINE")
