"""Engine ports of The Watcher. Routers call these ports and never an engine directly.

An adapter raises `EngineUnavailableError` when its engine cannot produce a result. It never
returns substitute output (ADR-0015, Context item 4). See docs/how-to/add-an-engine-port-adapter.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from runefoble_platform.stand_in_action import StandInAction
from the_watcher.models import (
    DMGuidanceRequest,
    DMNarrationResult,
    IntentResult,
    SpeechInputRequest,
    StandInRequest,
)


class IntentParser(ABC):
    """Turns player speech into a game intent."""

    engine_name: ClassVar[str]

    @abstractmethod
    async def parse(self, req: SpeechInputRequest, authorization: str | None) -> IntentResult:
        """Return the intent for one utterance. `authorization` is the speaker's bearer header.

        Raises EngineUnavailableError when the engine cannot parse the utterance.
        """


class StandInDecider(ABC):
    """Chooses the action of an absent player's character."""

    engine_name: ClassVar[str]

    @abstractmethod
    async def decide(self, req: StandInRequest) -> StandInAction:
        """Return one stand-in action with its penalties applied.

        Raises EngineUnavailableError when the engine cannot decide.
        """


class SceneNarrator(ABC):
    """Writes the Autonomous DM narration for a scene."""

    engine_name: ClassVar[str]

    @abstractmethod
    async def narrate(self, req: DMGuidanceRequest) -> DMNarrationResult:
        """Return one narration.

        Raises EngineUnavailableError when the engine cannot narrate.
        """
