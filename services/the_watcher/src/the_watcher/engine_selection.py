"""Selects The Watcher's engine adapters from settings.

`RUNEFOBLE_WATCHER_ENGINE` picks one engine family for all three ports. The lifespan builds
the ports once, so a missing worker URL stops start-up. Request handlers build them again
from the same settings, so each request reads the current environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from runefoble_platform.engine_ports import build_adapter
from the_watcher.adapters.heuristic_engines import (
    HeuristicIntentParser,
    HeuristicSceneNarrator,
    HeuristicStandInDecider,
)
from the_watcher.adapters.worker_engines import (
    WorkerIntentParser,
    WorkerSceneNarrator,
    WorkerStandInDecider,
)
from the_watcher.ports import IntentParser, SceneNarrator, StandInDecider
from the_watcher.watcher_ai import TheWatcherEngine

WatcherEngineName = Literal["inference_worker", "heuristic"]
WATCHER_ENGINE_SETTING = "RUNEFOBLE_WATCHER_ENGINE"


class WatcherEngineSettings(BaseSettings):
    """Engine selection. `RUNEFOBLE_WATCHER_ENGINE` defaults to the inference worker."""

    model_config = SettingsConfigDict(env_prefix="RUNEFOBLE_", extra="ignore")

    watcher_engine: WatcherEngineName = "inference_worker"
    inference_url: str | None = None
    board_state_url: str | None = None

    @field_validator("inference_url", "board_state_url", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


@dataclass(frozen=True)
class WatcherPorts:
    """The three engine ports that The Watcher routes use."""

    intent: IntentParser
    stand_in: StandInDecider
    narrator: SceneNarrator


def _worker_url(settings: WatcherEngineSettings) -> str:
    if settings.inference_url is None:
        raise RuntimeError(
            "RUNEFOBLE_WATCHER_ENGINE is 'inference_worker' but RUNEFOBLE_INFERENCE_URL is not set. "
            "Set the inference worker URL, or set RUNEFOBLE_WATCHER_ENGINE to 'heuristic'."
        )
    return settings.inference_url


def build_watcher_ports(
    settings: WatcherEngineSettings, heuristic: TheWatcherEngine
) -> WatcherPorts:
    """Build the three ports that `settings` selects. Only the selected factories run."""
    setting = WATCHER_ENGINE_SETTING
    value = settings.watcher_engine
    return WatcherPorts(
        intent=build_adapter(
            setting,
            value,
            {
                "inference_worker": lambda: WorkerIntentParser(
                    base_url=_worker_url(settings),
                    board_state_url=settings.board_state_url,
                ),
                "heuristic": lambda: HeuristicIntentParser(heuristic),
            },
        ),
        stand_in=build_adapter(
            setting,
            value,
            {
                "inference_worker": lambda: WorkerStandInDecider(_worker_url(settings)),
                "heuristic": lambda: HeuristicStandInDecider(heuristic),
            },
        ),
        narrator=build_adapter(
            setting,
            value,
            {
                "inference_worker": lambda: WorkerSceneNarrator(_worker_url(settings)),
                "heuristic": HeuristicSceneNarrator,
            },
        ),
    )


def load_watcher_ports(heuristic: TheWatcherEngine) -> WatcherPorts:
    """Read the current environment and build the selected ports. Raises on a bad setting."""
    return build_watcher_ports(WatcherEngineSettings(), heuristic)
