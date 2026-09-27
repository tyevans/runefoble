"""Speech-to-intent and tactical movement parser coordinator for The Watcher."""

from __future__ import annotations

from typing import Any

from the_watcher.grammars import (
    ATTACK_PATTERN,
    CARDINAL_DIR_FIRST_PATTERN,
    CARDINAL_DIST_FIRST_PATTERN,
    COORD_PATTERN,
    DICE_PATTERN,
    FLANK_PATTERN,
    GENERIC_ATTACK_PATTERN,
    GENERIC_CHECK_PATTERN,
    MOVE_TO_TOKEN_PATTERN,
    SKILL_PATTERN,
    SPELL_PATTERN,
    SPELL_TARGET_COORD_PATTERN,
)
from the_watcher.intent.reactions import parse_reaction_intent
from the_watcher.models import IntentResult
from the_watcher.spatial import (
    calculate_bounded_destination,
    calculate_steps,
    compute_directional_deltas,
)


def _intent(
    action: str, conf: float, params: dict[str, Any], target: str | None, details: str, reply: str
) -> IntentResult:
    return IntentResult(
        action_type=action,
        confidence=conf,
        parameters=params,
        target=target,
        details=details,
        watcher_reply=reply,
    )


class SpeechIntentParser:
    """Parses natural spoken language transcripts into game actions and board mutations."""

    compute_directional_deltas = staticmethod(compute_directional_deltas)
    calculate_steps = staticmethod(calculate_steps)
    calculate_bounded_destination = staticmethod(calculate_bounded_destination)

    _coord_pattern = COORD_PATTERN
    _cardinal_pattern_dist_first = CARDINAL_DIST_FIRST_PATTERN
    _cardinal_pattern_dir_first = CARDINAL_DIR_FIRST_PATTERN
    _flank_pattern = FLANK_PATTERN
    _spell_pattern = SPELL_PATTERN
    _move_to_token_pattern = MOVE_TO_TOKEN_PATTERN
    _attack_pattern = ATTACK_PATTERN
    _skill_pattern = SKILL_PATTERN
    _generic_check_pattern = GENERIC_CHECK_PATTERN
    _dice_pattern = DICE_PATTERN

    def _build_cardinal_intent(
        self, direction: str, dist: int, unit: str | None, speaker: str
    ) -> IntentResult:
        dir_clean = direction.lower()
        steps = self.calculate_steps(dist, unit)
        dx, dy = self.compute_directional_deltas(dir_clean, steps)
        p = {"action": "move", "dx": dx, "dy": dy, "steps": steps, "direction": dir_clean}
        p["raw_distance"], p["unit"] = dist, unit or "squares"
        return _intent(
            "move",
            0.95,
            p,
            dir_clean,
            f"Move {steps} squares {dir_clean}",
            f"The Watcher guides {speaker} {steps} steps {dir_clean}.",
        )

    def parse_speech_intent(self, transcript: str, speaker_name: str) -> IntentResult:
        """Parse natural spoken language into game actions and board mutations."""
        text = transcript.strip()

        if r := parse_reaction_intent(text, speaker_name):
            reply = f"{speaker_name} reacts: {r.trigger_phrase}!"
            return _intent(
                r.action_type, r.confidence, r.parameters, r.target, r.trigger_phrase, reply
            )

        # 1. Coordinate movement: "move to 5, 8"
        if m := self._coord_pattern.search(text):
            x, y = int(m.group(1)), int(m.group(2))
            p = {"action": "move_to_coordinates", "to_x": x, "to_y": y}
            p["target_x"], p["target_y"] = x, y
            return _intent(
                "move",
                0.95,
                p,
                f"{x}, {y}",
                f"Coordinates ({x}, {y})",
                f"The Watcher navigates {speaker_name} to ({x}, {y}).",
            )

        # 2. Cardinal distance movement
        if m := self._cardinal_pattern_dist_first.search(text):
            return self._build_cardinal_intent(
                m.group(3), int(m.group(1)), m.group(2), speaker_name
            )
        if m := self._cardinal_pattern_dir_first.search(text):
            return self._build_cardinal_intent(
                m.group(1), int(m.group(2)), m.group(3), speaker_name
            )

        # 3. Flanking intent: "flank the skeleton"
        if m := self._flank_pattern.search(text):
            tgt = m.group(1).strip()
            p = {"action": "flank", "target_token": tgt, "target": tgt}
            return _intent(
                "move",
                0.92,
                p,
                tgt,
                f"Flank {tgt}",
                f"The Watcher repositions {speaker_name} to flank {tgt}.",
            )

        # 4. Spellcasting intent: "cast fireball at 4, 6"
        if m := self._spell_pattern.search(text):
            spell, raw_tgt = m.group(1).strip(), m.group(2).strip() if m.group(2) else None
            p: dict[str, Any] = {"action": "cast_spell", "spell": spell}
            if raw_tgt:
                p["target"] = raw_tgt
                if cm := SPELL_TARGET_COORD_PATTERN.search(raw_tgt):
                    if cm.group(1) is not None and cm.group(2) is not None:
                        p["target_x"], p["target_y"] = int(cm.group(1)), int(cm.group(2))
                    elif cm.group(3) is not None and cm.group(4) is not None:
                        p["target_x"], p["target_y"] = (
                            ord(cm.group(3).upper()) - ord("A"),
                            int(cm.group(4)) - 1,
                        )

            reply = (
                f"{speaker_name} casts {spell}"
                + (f" at {raw_tgt}" if raw_tgt else "")
                + "! Arcane energy surges."
            )
            return _intent("cast_spell", 0.92, p, raw_tgt, f"Cast {spell}", reply)

        # 5. Move to target token: "move to the goblin archer"
        if m := self._move_to_token_pattern.search(text):
            tgt = m.group(1).strip()
            p = {"action": "move_to_target", "target_token": tgt, "target": tgt}
            return _intent(
                "move",
                0.90,
                p,
                tgt,
                f"Move to {tgt}",
                f"The Watcher moves {speaker_name} towards {tgt}.",
            )

        # 6. Attack: "attack goblin with longsword"
        if m := self._attack_pattern.search(text):
            tgt, weapon = m.group(1).strip(), m.group(2).strip() if m.group(2) else None
            p = {"action": "attack", "target": tgt, **({"weapon": weapon} if weapon else {})}
            reply = (
                f"{speaker_name} attacks {tgt}"
                + (f" with {weapon}" if weapon else "")
                + "! Roll for attack (1d20 + modifier)."
            )
            return _intent("attack", 0.90, p, tgt, f"Attack {tgt}", reply)

        if GENERIC_ATTACK_PATTERN.search(text):
            p = {"action": "attack", "target": "nearest_enemy"}
            reply = f"{speaker_name} initiates combat! Roll for attack (1d20 + modifier)."
            return _intent("attack", 0.90, p, "nearest_enemy", "Attack nearest enemy", reply)

        # 7. Skill checks: "stealth check"
        if m := (self._skill_pattern.search(text) or self._generic_check_pattern.search(text)):
            sk = m.group(1).lower().strip()
            conf = 0.90 if self._skill_pattern.search(text) else 0.88
            p = {"action": "skill_check", "skill": sk, "dice_notation": "1d20"}
            reply = f"{speaker_name} performs a {sk} check! Roll 1d20 + modifier."
            return _intent("skill_check", conf, p, sk, f"Skill check: {sk}", reply)

        # 8. Dice rolls: "roll 1d20"
        if m := self._dice_pattern.search(text):
            notat = m.group(1) if not m.group(1).startswith("d") else f"1{m.group(1)}"
            p = {"action": "roll_dice", "notation": notat}
            reply = f"{speaker_name} rolls {notat}."
            return _intent("roll_dice", 0.95, p, notat, f"Roll {notat}", reply)

        reply = f"The Watcher records the action: '{text}'. Fate awaits the outcome."
        return _intent("narrative", 0.85, {"raw_transcript": text}, None, text, reply)
