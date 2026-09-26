"""The Watcher AI Gameplay System.

Orchestrates speech-to-intent interpretation, tactical board animations,
autonomous Dungeon Mastering, and missing player stand-in emulation with penalties.
"""

from typing import Any, Dict, List, Optional
import re
from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    action_type: str  # "move", "attack", "cast_spell", "narrative", "roll_dice"
    confidence: float
    parameters: Dict[str, Any]
    watcher_reply: str


class StandInAction(BaseModel):
    character_name: str
    action_description: str
    dialogue: str
    penalty_influence: Optional[str] = None
    dice_roll_required: Optional[str] = None


class TheWatcherEngine:
    """Core intelligence engine for The Watcher."""

    def __init__(self):
        # Directional mapping regex
        self._move_pattern = re.compile(
            r"(?:move|walk|step|charge|run)\s+(\d+)\s*(?:squares?|hexes?|spaces?|steps?)?\s*(north|south|east|west|up|down|left|right)",
            re.IGNORECASE,
        )

    def parse_speech_intent(self, transcript: str, speaker_name: str) -> IntentResult:
        """Parse natural spoken language into game actions and board mutations."""
        transcript_clean = transcript.strip()

        # Check movement pattern
        match = self._move_pattern.search(transcript_clean)
        if match:
            steps = int(match.group(1))
            direction = match.group(2).lower()
            dx, dy = 0, 0
            if direction in ("north", "up"):
                dy = -steps
            elif direction in ("south", "down"):
                dy = steps
            elif direction in ("east", "right"):
                dx = steps
            elif direction in ("west", "left"):
                dx = -steps

            return IntentResult(
                action_type="move",
                confidence=0.95,
                parameters={"dx": dx, "dy": dy, "steps": steps, "direction": direction},
                watcher_reply=f"The Watcher guides {speaker_name} {steps} steps {direction}.",
            )

        # Check attack or combat intent
        if re.search(r"\b(attack|strike|hit|shoot|slash)\b", transcript_clean, re.IGNORECASE):
            return IntentResult(
                action_type="attack",
                confidence=0.90,
                parameters={"action": "attack", "target": "nearest_enemy"},
                watcher_reply=f"{speaker_name} initiates combat! Roll for attack (1d20 + modifier).",
            )

        # Default: Narrative action for DM arbitration
        return IntentResult(
            action_type="narrative",
            confidence=0.85,
            parameters={"raw_transcript": transcript_clean},
            watcher_reply=f"The Watcher records the action: '{transcript_clean}'. Fate awaits the outcome.",
        )

    def generate_stand_in_action(
        self,
        character_name: str,
        character_class: str,
        penalties: List[str],
        scene_context: str,
    ) -> StandInAction:
        """Simulate an action and dialogue for an absent player's character.

        Applies DM-inflicted penalties like 'drunk' or 'foolishness'.
        """
        if "drunk" in penalties:
            return StandInAction(
                character_name=character_name,
                action_description=f"{character_name} sways on their heels, hiccuping loudly, before swinging at a shadow.",
                dialogue=f"\"Hic! Don't you worry, my friends! The ale only sharpens my blade!\"",
                penalty_influence="Drunk: Disadvantage on finesse and perception checks.",
                dice_roll_required="1d20-2",
            )

        if "foolishness" in penalties:
            return StandInAction(
                character_name=character_name,
                action_description=f"{character_name} recklessly charges headfirst towards the most imposing threat in the room.",
                dialogue="\"Danger? Ha! I eat danger for breakfast! Follow my glory!\"",
                penalty_influence="Foolishness: AI ignores tactical cover and exposes flank.",
                dice_roll_required="1d20",
            )

        # Standard stand-in persona
        return StandInAction(
            character_name=character_name,
            action_description=f"{character_name} takes a guarded defensive posture, watching the party's flank.",
            dialogue="\"Hold the line. We press forward together.\"",
            penalty_influence=None,
            dice_roll_required="1d20+2",
        )
