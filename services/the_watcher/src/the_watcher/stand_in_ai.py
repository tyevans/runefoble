"""Missing player stand-in AI engine facade delegating to guardrail, persona, and recap sub-modules."""

from typing import Any

from the_watcher.models import StandInAction
from the_watcher.stand_in_guardrails import evaluate_tactical_guardrails
from the_watcher.stand_in_persona import apply_penalty_modifiers
from the_watcher.stand_in_recap import generate_absentee_recap

__all__ = [
    "StandInAIEngine",
    "apply_penalty_modifiers",
    "evaluate_tactical_guardrails",
    "generate_absentee_recap",
]


class StandInAIEngine:
    """Facade simulating actions, dialogue, and recaps for absent players."""

    def generate_stand_in_action(
        self,
        character_name: str,
        character_class: str,
        penalties: list[str],
        scene_context: str,
        personality_traits: list[str] | None = None,
        guardrails: dict[str, Any] | None = None,
    ) -> StandInAction:
        """Simulate an action and dialogue for an absent player's character.

        Applies tactical guardrail policies first; falls back to persona & penalty simulation.
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
