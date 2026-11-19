"""The Watcher AI Gameplay System.

Orchestrates speech-to-intent interpretation, tactical board animations,
autonomous Dungeon Mastering, and missing player stand-in emulation with penalties.
"""

from typing import Any

from runefoble_platform.stand_in_action import StandInAction
from runefoble_platform.stand_in_guardrails import StandInGuardrailPolicy
from the_watcher.compound_actions import CompoundActionEngine
from the_watcher.disambiguation import DisambiguationEngine
from the_watcher.intent.reactions import ReactionIntent, parse_reaction_intent
from the_watcher.models import IntentResult, StandInRecapResponse
from the_watcher.movement_parser import SpeechIntentParser
from the_watcher.spatial import calculate_bounded_destination
from the_watcher.stand_in_guardrails import evaluate_tactical_guardrails
from the_watcher.stand_in_persona import apply_penalty_modifiers
from the_watcher.stand_in_recap import generate_absentee_recap

__all__ = [
    "IntentResult",
    "ReactionIntent",
    "StandInAction",
    "StandInRecapResponse",
    "TheWatcherEngine",
    "parse_reaction_intent",
]


class TheWatcherEngine:
    """Core intelligence engine for The Watcher combining speech intent and stand-in AI."""

    def __init__(self) -> None:
        self._movement_parser = SpeechIntentParser()
        self._disambiguation = DisambiguationEngine()
        self._compound_actions = CompoundActionEngine(self._movement_parser)

    @property
    def disambiguation(self) -> DisambiguationEngine:
        return self._disambiguation

    @property
    def compound_actions(self) -> CompoundActionEngine:
        return self._compound_actions

    def calculate_bounded_destination(
        self,
        from_x: int,
        from_y: int,
        dx: int,
        dy: int,
        cols: int = 12,
        rows: int = 12,
    ) -> tuple[int, int]:
        """Calculate target coordinates clamped strictly within tactical grid bounds."""
        return calculate_bounded_destination(
            from_x=from_x,
            from_y=from_y,
            dx=dx,
            dy=dy,
            cols=cols,
            rows=rows,
        )

    def parse_speech_intent(self, transcript: str, speaker_name: str) -> IntentResult:
        """Parse natural spoken language into game actions and board mutations."""
        return self._movement_parser.parse_speech_intent(transcript, speaker_name)

    def parse_reaction_intent(
        self, transcript: str, speaker_name: str = ""
    ) -> ReactionIntent | None:
        """Parse spoken reaction interrupt or conditional ready action intent."""
        return parse_reaction_intent(transcript, speaker_name)

    def generate_stand_in_action(
        self,
        character_name: str,
        character_class: str,
        penalties: list[str],
        scene_context: str,
        personality_traits: list[str] | None = None,
        guardrails: StandInGuardrailPolicy | None = None,
    ) -> StandInAction:
        """Simulate an action and dialogue for an absent player's character.

        Tactical guardrails apply first. Persona and penalty simulation apply when none fires.
        """
        guardrail_action = evaluate_tactical_guardrails(
            character_name=character_name,
            character_class=character_class,
            penalties=penalties,
            scene_context=scene_context,
            personality_traits=personality_traits,
            guardrails=guardrails,
        )
        if guardrail_action is not None:
            return guardrail_action

        return apply_penalty_modifiers(
            character_name=character_name,
            character_class=character_class,
            penalties=penalties,
            scene_context=scene_context,
            personality_traits=personality_traits,
        )

    def generate_stand_in_recap(
        self,
        character_name: str,
        actions: list[Any],
        penalties: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate a humorous absentee session recap for a returning player."""
        return generate_absentee_recap(
            character_name=character_name,
            actions=actions,
            penalties=penalties,
        )
