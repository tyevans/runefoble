"""The Watcher AI Gameplay System.

Orchestrates speech-to-intent interpretation, tactical board animations,
autonomous Dungeon Mastering, and missing player stand-in emulation with penalties.
"""

import re
from typing import Any

from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    action_type: str  # "move", "attack", "cast_spell", "skill_check", "narrative", "roll_dice"
    confidence: float
    parameters: dict[str, Any] = Field(default_factory=dict)
    watcher_reply: str
    target: str | None = None
    details: str | None = None


class StandInAction(BaseModel):
    character_name: str
    action_description: str
    dialogue: str
    penalty_influence: str | None = None
    dice_roll_required: str | None = None


class TheWatcherEngine:
    """Core intelligence engine for The Watcher."""

    def __init__(self) -> None:
        # 1. Coordinate movement: e.g. "move to 5, 8", "step to (5, 8)", "go to 5, 8"
        self._coord_pattern = re.compile(
            r"\b(?:move|step|walk|go|travel|run|dash|advance|retreat)\s+(?:to|towards|at)?\s*\(?\s*(\d+)\s*,\s*(\d+)\s*\)?",
            re.IGNORECASE,
        )

        # 2a. Cardinal distance movement: e.g. "move 3 squares north", "step 15 feet south", "advance 2 east", "retreat 1 west"
        self._cardinal_pattern_dist_first = re.compile(
            r"\b(?:move|step|walk|charge|run|advance|retreat|fall back|sprint|dash|head|go)\s+(\d+)\s*(feet|foot|ft|squares?|hexes?|spaces?|steps?|tiles?)?\s*(north|south|east|west|up|down|left|right|northeast|northwest|southeast|southwest|north-east|north-west|south-east|south-west)\b",
            re.IGNORECASE,
        )

        # 2b. Cardinal distance movement with direction first: e.g. "move north 3 squares", "walk east 10 feet"
        self._cardinal_pattern_dir_first = re.compile(
            r"\b(?:move|step|walk|charge|run|advance|retreat|fall back|sprint|dash|head|go)\s+(north|south|east|west|up|down|left|right|northeast|northwest|southeast|southwest|north-east|north-west|south-east|south-west)\s+(\d+)\s*(feet|foot|ft|squares?|hexes?|spaces?|steps?|tiles?)?\b",
            re.IGNORECASE,
        )

        # 3. Flanking intent: e.g. "flank the skeleton"
        self._flank_pattern = re.compile(
            r"\bflank\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:[.!?,]|$)",
            re.IGNORECASE,
        )

        # 4. Spellcasting: e.g. "cast fireball at 4, 6", "cast magic missile at goblin archer"
        self._spell_pattern = re.compile(
            r"\b(?:cast|invoke|channel)\s+([a-zA-Z0-9_\-\s]+?)(?:\s+(?:at|on|towards)\s+(?:the\s+)?([a-zA-Z0-9_\-,\s()]+))?(?:[.!?,]|$)",
            re.IGNORECASE,
        )

        # 5. Move to target token: e.g. "move to the goblin archer", "advance towards the orc"
        self._move_to_token_pattern = re.compile(
            r"\b(?:move|step|walk|charge|run|advance|retreat|go)\s+(?:to|towards|next to|near|adjacent to)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:[.!?,]|$)",
            re.IGNORECASE,
        )

        # 6. Attack: e.g. "attack goblin with longsword", "I slash at the goblin with my sword!", "shoot orc"
        self._attack_pattern = re.compile(
            r"\b(?:attack|strike|hit|shoot|slash|stab|cleave|smite)\s+(?:at\s+)?(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+with\s+(?:my\s+|a\s+|an\s+)?([a-zA-Z0-9_\-\s]+))?(?:[.!?,]|$)",
            re.IGNORECASE,
        )

        # 7. Skill checks: e.g. "stealth check", "make an athletics check", "roll perception"
        skills = (
            "stealth|perception|athletics|acrobatics|insight|investigation|arcana|"
            "history|nature|religion|animal handling|medicine|survival|deception|"
            "intimidation|performance|persuasion|initiative"
        )
        self._skill_pattern = re.compile(
            rf"\b(?:make\s+an?|roll\s+an?|roll\s+for\s+)?\s*({skills})\s*(?:check)?\b",
            re.IGNORECASE,
        )
        self._generic_check_pattern = re.compile(
            r"\b(?:make\s+an?|roll\s+an?|roll\s+for\s+)?\s*([a-zA-Z]+)\s+check\b",
            re.IGNORECASE,
        )

        # 8. Dice rolls: e.g. "roll 1d20", "roll 2d6+3", "roll a d20"
        self._dice_pattern = re.compile(
            r"\broll\s+(?:a\s+)?(\d*d\d+(?:[+-]\d+)?)\b",
            re.IGNORECASE,
        )

    def _compute_directional_deltas(self, direction: str, steps: int) -> tuple[int, int]:
        direction_clean = direction.lower().replace("-", "")
        dx, dy = 0, 0
        if direction_clean in ("north", "up"):
            dy = -steps
        elif direction_clean in ("south", "down"):
            dy = steps
        elif direction_clean in ("east", "right"):
            dx = steps
        elif direction_clean in ("west", "left"):
            dx = -steps
        elif direction_clean == "northeast":
            dx = steps
            dy = -steps
        elif direction_clean == "northwest":
            dx = -steps
            dy = -steps
        elif direction_clean == "southeast":
            dx = steps
            dy = steps
        elif direction_clean == "southwest":
            dx = -steps
            dy = steps
        return dx, dy

    def _calculate_steps(self, raw_distance: int, unit: str | None) -> int:
        unit_lower = (unit or "").lower()
        if unit_lower in ("feet", "foot", "ft"):
            return max(1, raw_distance // 5) if raw_distance > 0 else 0
        return raw_distance

    def calculate_bounded_destination(
        self,
        from_x: int,
        from_y: int,
        dx: int,
        dy: int,
        cols: int = 12,
        rows: int = 12,
    ) -> tuple[int, int]:
        """Calculate target coordinates clamped strictly within tactical grid bounds [0, cols-1] and [0, rows-1]."""
        to_x = max(0, min(cols - 1, from_x + dx))
        to_y = max(0, min(rows - 1, from_y + dy))
        return to_x, to_y

    def parse_speech_intent(self, transcript: str, speaker_name: str) -> IntentResult:
        """Parse natural spoken language into game actions and board mutations."""
        transcript_clean = transcript.strip()

        # 1. Check coordinate movement: "move to 5, 8"
        coord_match = self._coord_pattern.search(transcript_clean)
        if coord_match:
            to_x = int(coord_match.group(1))
            to_y = int(coord_match.group(2))
            return IntentResult(
                action_type="move",
                confidence=0.95,
                parameters={
                    "action": "move_to_coordinates",
                    "to_x": to_x,
                    "to_y": to_y,
                    "target_x": to_x,
                    "target_y": to_y,
                },
                target=f"{to_x}, {to_y}",
                details=f"Coordinates ({to_x}, {to_y})",
                watcher_reply=f"The Watcher navigates {speaker_name} to ({to_x}, {to_y}).",
            )

        # 2. Check cardinal distance movement: "move 3 squares north", "step 15 feet south", "advance 2 east"
        cardinal_match = self._cardinal_pattern_dist_first.search(transcript_clean)
        if cardinal_match:
            raw_dist = int(cardinal_match.group(1))
            unit = cardinal_match.group(2)
            direction = cardinal_match.group(3).lower()
            steps = self._calculate_steps(raw_dist, unit)
            dx, dy = self._compute_directional_deltas(direction, steps)
            return IntentResult(
                action_type="move",
                confidence=0.95,
                parameters={
                    "action": "move",
                    "dx": dx,
                    "dy": dy,
                    "steps": steps,
                    "direction": direction,
                    "raw_distance": raw_dist,
                    "unit": unit or "squares",
                },
                target=direction,
                details=f"Move {steps} squares {direction}",
                watcher_reply=f"The Watcher guides {speaker_name} {steps} steps {direction}.",
            )

        cardinal_dir_match = self._cardinal_pattern_dir_first.search(transcript_clean)
        if cardinal_dir_match:
            direction = cardinal_dir_match.group(1).lower()
            raw_dist = int(cardinal_dir_match.group(2))
            unit = cardinal_dir_match.group(3)
            steps = self._calculate_steps(raw_dist, unit)
            dx, dy = self._compute_directional_deltas(direction, steps)
            return IntentResult(
                action_type="move",
                confidence=0.95,
                parameters={
                    "action": "move",
                    "dx": dx,
                    "dy": dy,
                    "steps": steps,
                    "direction": direction,
                    "raw_distance": raw_dist,
                    "unit": unit or "squares",
                },
                target=direction,
                details=f"Move {steps} squares {direction}",
                watcher_reply=f"The Watcher guides {speaker_name} {steps} steps {direction}.",
            )

        # 3. Check flanking intent: "flank the skeleton"
        flank_match = self._flank_pattern.search(transcript_clean)
        if flank_match:
            target = flank_match.group(1).strip()
            return IntentResult(
                action_type="move",
                confidence=0.92,
                parameters={"action": "flank", "target_token": target, "target": target},
                target=target,
                details=f"Flank {target}",
                watcher_reply=f"The Watcher repositions {speaker_name} to flank {target}.",
            )

        # 4. Check spellcasting intent: "cast fireball at 4, 6"
        spell_match = self._spell_pattern.search(transcript_clean)
        if spell_match:
            spell_name = spell_match.group(1).strip()
            target_raw = spell_match.group(2).strip() if spell_match.group(2) else None
            params: dict[str, Any] = {"action": "cast_spell", "spell": spell_name}
            target_str = target_raw
            if target_raw:
                params["target"] = target_raw
                coord_m = re.search(r"\(?\s*(\d+)\s*,\s*(\d+)\s*\)?", target_raw)
                if coord_m:
                    params["target_x"] = int(coord_m.group(1))
                    params["target_y"] = int(coord_m.group(2))
            reply = f"{speaker_name} casts {spell_name}"
            if target_raw:
                reply += f" at {target_raw}"
            reply += "! Arcane energy surges."
            return IntentResult(
                action_type="cast_spell",
                confidence=0.92,
                parameters=params,
                target=target_str,
                details=f"Cast {spell_name}",
                watcher_reply=reply,
            )

        # 5. Check move to target token: "move to the goblin archer"
        move_to_token_match = self._move_to_token_pattern.search(transcript_clean)
        if move_to_token_match:
            target = move_to_token_match.group(1).strip()
            return IntentResult(
                action_type="move",
                confidence=0.90,
                parameters={"action": "move_to_target", "target_token": target, "target": target},
                target=target,
                details=f"Move to {target}",
                watcher_reply=f"The Watcher moves {speaker_name} towards {target}.",
            )

        # 6. Check attack or combat intent: "attack goblin with longsword", "I slash at the goblin with my sword!"
        attack_match = self._attack_pattern.search(transcript_clean)
        if attack_match:
            target = attack_match.group(1).strip()
            weapon = attack_match.group(2).strip() if attack_match.group(2) else None
            params = {"action": "attack", "target": target}
            if weapon:
                params["weapon"] = weapon
            reply = f"{speaker_name} attacks {target}"
            if weapon:
                reply += f" with {weapon}"
            reply += "! Roll for attack (1d20 + modifier)."
            return IntentResult(
                action_type="attack",
                confidence=0.90,
                parameters=params,
                target=target,
                details=f"Attack {target}",
                watcher_reply=reply,
            )

        if re.search(
            r"\b(attack|strike|hit|shoot|slash|cleave|smite)\b", transcript_clean, re.IGNORECASE
        ):
            return IntentResult(
                action_type="attack",
                confidence=0.90,
                parameters={"action": "attack", "target": "nearest_enemy"},
                target="nearest_enemy",
                details="Attack nearest enemy",
                watcher_reply=f"{speaker_name} initiates combat! Roll for attack (1d20 + modifier).",
            )

        # 7. Check skill check: "stealth check"
        skill_match = self._skill_pattern.search(transcript_clean)
        if skill_match:
            skill_name = skill_match.group(1).lower().strip()
            return IntentResult(
                action_type="skill_check",
                confidence=0.90,
                parameters={"action": "skill_check", "skill": skill_name, "dice_notation": "1d20"},
                target=skill_name,
                details=f"Skill check: {skill_name}",
                watcher_reply=f"{speaker_name} performs a {skill_name} check! Roll 1d20 + modifier.",
            )

        generic_check_match = self._generic_check_pattern.search(transcript_clean)
        if generic_check_match:
            skill_name = generic_check_match.group(1).lower().strip()
            return IntentResult(
                action_type="skill_check",
                confidence=0.88,
                parameters={"action": "skill_check", "skill": skill_name, "dice_notation": "1d20"},
                target=skill_name,
                details=f"Skill check: {skill_name}",
                watcher_reply=f"{speaker_name} performs a {skill_name} check! Roll 1d20 + modifier.",
            )

        # 8. Check dice roll: "roll 1d20"
        dice_match = self._dice_pattern.search(transcript_clean)
        if dice_match:
            notation = dice_match.group(1)
            if notation.startswith("d"):
                notation = "1" + notation
            return IntentResult(
                action_type="roll_dice",
                confidence=0.95,
                parameters={"action": "roll_dice", "notation": notation},
                target=notation,
                details=f"Roll {notation}",
                watcher_reply=f"{speaker_name} rolls {notation}.",
            )

        # Default: Narrative action for DM arbitration
        return IntentResult(
            action_type="narrative",
            confidence=0.85,
            parameters={"raw_transcript": transcript_clean},
            details=transcript_clean,
            watcher_reply=f"The Watcher records the action: '{transcript_clean}'. Fate awaits the outcome.",
        )

    def generate_stand_in_action(
        self,
        character_name: str,
        character_class: str,
        penalties: list[str],
        scene_context: str,
    ) -> StandInAction:
        """Simulate an action and dialogue for an absent player's character.

        Applies DM-inflicted penalties like 'drunk' or 'foolishness'.
        """
        if "drunk" in penalties:
            return StandInAction(
                character_name=character_name,
                action_description=f"{character_name} sways on their heels, hiccuping loudly, before swinging at a shadow.",
                dialogue='"Hic! Don\'t you worry, my friends! The ale only sharpens my blade!"',
                penalty_influence="Drunk: Disadvantage on finesse and perception checks.",
                dice_roll_required="1d20-2",
            )

        if "foolishness" in penalties:
            return StandInAction(
                character_name=character_name,
                action_description=f"{character_name} recklessly charges headfirst towards the most imposing threat in the room.",
                dialogue='"Danger? Ha! I eat danger for breakfast! Follow my glory!"',
                penalty_influence="Foolishness: AI ignores tactical cover and exposes flank.",
                dice_roll_required="1d20",
            )

        # Standard stand-in persona
        return StandInAction(
            character_name=character_name,
            action_description=f"{character_name} takes a guarded defensive posture, watching the party's flank.",
            dialogue='"Hold the line. We press forward together."',
            penalty_influence=None,
            dice_roll_required="1d20+2",
        )
