"""Selects The Watcher's engine adapters from settings, one setting per port (ADR-0022 d).

`RUNEFOBLE_WATCHER_INTENT_ENGINE`, `RUNEFOBLE_WATCHER_STAND_IN_ENGINE` and
`RUNEFOBLE_WATCHER_NARRATION_ENGINE` each accept `inference_worker` or `none`. `none` means the
port has no engine. The intent port always parses with the grammar first (ADR-0022 a). The lifespan
builds the ports once, so a missing worker URL stops start-up. Request handlers build them again
from the same settings, so each request reads the current environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from runefoble_platform.engine_ports import build_adapter
from the_watcher.adapters.grammar_first import GrammarFirstIntentParser
from the_watcher.adapters.unconfigured import UnconfiguredSceneNarrator, UnconfiguredStandInDecider
from the_watcher.adapters.worker_engines import (
    WorkerIntentParser,
    WorkerSceneNarrator,
    WorkerStandInDecider,
)
from the_watcher.ports import IntentParser, SceneNarrator, StandInDecider
from the_watcher.watcher_ai import TheWatcherEngine

WatcherEngineName = Literal["inference_worker", "none"]
INTENT_ENGINE_SETTING = "RUNEFOBLE_WATCHER_INTENT_ENGINE"
STAND_IN_ENGINE_SETTING = "RUNEFOBLE_WATCHER_STAND_IN_ENGINE"
NARRATION_ENGINE_SETTING = "RUNEFOBLE_WATCHER_NARRATION_ENGINE"
NONE_ENGINE = "none"


class WatcherEngineSettings(BaseSettings):
    """Engine selection for each port. Every port defaults to `none` (not configured)."""

    model_config = SettingsConfigDict(env_prefix="RUNEFOBLE_", extra="ignore")

    watcher_intent_engine: WatcherEngineName = "none"
    watcher_stand_in_engine: WatcherEngineName = "none"
    watcher_narration_engine: WatcherEngineName = "none"
    inference_url: str | None = None
    board_state_url: str | None = None
    # The worker refuses a call without it (ADR-0015 e). The Watcher then answers 503.
    service_credential: SecretStr | None = None
    # Call budgets in seconds. A call that runs out of budget answers 503 (ADR-0015).
    watcher_intent_timeout_s: float = Field(default=2.0, gt=0)
    watcher_stand_in_timeout_s: float = Field(default=10.0, gt=0)
    watcher_narration_timeout_s: float = Field(default=10.0, gt=0)
    watcher_board_timeout_s: float = Field(default=2.0, gt=0)
    watcher_proposal_timeout_s: float = Field(default=2.0, gt=0)

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
            "A Watcher engine port is 'inference_worker' but RUNEFOBLE_INFERENCE_URL is not set. "
            "Set the inference worker URL, or set the port setting to 'none'."
        )
    return settings.inference_url


def build_watcher_ports(settings: WatcherEngineSettings, grammar: TheWatcherEngine) -> WatcherPorts:
    """Build the three ports that `settings` selects. Only the selected factories run.

    `grammar` is the rule parser. The intent port runs it first for every transcript.
    """
    return WatcherPorts(
        intent=_intent_port(settings, grammar),
        stand_in=build_adapter(
            STAND_IN_ENGINE_SETTING,
            settings.watcher_stand_in_engine,
            {
                "inference_worker": lambda: WorkerStandInDecider(
                    _worker_url(settings),
                    settings.service_credential,
                    timeout_s=settings.watcher_stand_in_timeout_s,
                ),
                NONE_ENGINE: UnconfiguredStandInDecider,
            },
        ),
        narrator=build_adapter(
            NARRATION_ENGINE_SETTING,
            settings.watcher_narration_engine,
            {
                "inference_worker": lambda: WorkerSceneNarrator(
                    _worker_url(settings),
                    settings.service_credential,
                    timeout_s=settings.watcher_narration_timeout_s,
                ),
                NONE_ENGINE: UnconfiguredSceneNarrator,
            },
        ),
    )


def _intent_port(settings: WatcherEngineSettings, grammar: TheWatcherEngine) -> IntentParser:
    """The grammar always runs. The worker is the fallthrough only when its setting selects it."""
    llm: IntentParser | None = build_adapter(
        INTENT_ENGINE_SETTING,
        settings.watcher_intent_engine,
        {
            "inference_worker": lambda: WorkerIntentParser(
                base_url=_worker_url(settings),
                board_state_url=settings.board_state_url,
                credential=settings.service_credential,
                intent_timeout_s=settings.watcher_intent_timeout_s,
                board_timeout_s=settings.watcher_board_timeout_s,
            ),
            NONE_ENGINE: lambda: None,
        },
    )
    return GrammarFirstIntentParser(grammar, llm)


def load_watcher_ports(grammar: TheWatcherEngine) -> WatcherPorts:
    """Read the current environment and build the selected ports. Raises on a bad setting."""
    return build_watcher_ports(WatcherEngineSettings(), grammar)
