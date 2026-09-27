"""Spoken reaction interrupts and ready-action intent grammar and extraction."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

_SHIELD = re.compile(r"\b(?:i\s+cast\s+|cast\s+)?shield(?:\s+spell)?\b", re.I)
_COUNTER = re.compile(r"\b(?:i\s+cast\s+|cast\s+)?counterspell(?:\s+(?:that|the\s+spell))?\b", re.I)
_OPP_ATK = re.compile(
    r"\b(?:i\s+(?:take|make|use)\s+(?:an?\s+)?)?opportunity\s+attack(?:\s+(?:on|against|at)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?))?(?:[.!?,]|$)",
    re.I,
)
_ABSORB = re.compile(r"\b(?:i\s+cast\s+|cast\s+)?absorb\s+elements\b", re.I)
_HELLISH = re.compile(
    r"\b(?:i\s+cast\s+|cast\s+)?hellish\s+rebuke(?:\s+(?:at|on)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?))?\b",
    re.I,
)
_SILVERY = re.compile(
    r"\b(?:i\s+cast\s+|cast\s+)?silvery\s+barbs(?:\s+(?:on|at)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?))?\b",
    re.I,
)
_DEFENSE = re.compile(r"\b(?:i\s+use\s+)?(uncanny\s+dodge|parry|deflect\s+missiles)\b", re.I)
_READY = re.compile(
    r"\b(?:i\s+)?ready\s+(?:my\s+|an?\s+)?(.+?)\s+(?:if|when)\s+(.+?)(?:[.!?,]|$)", re.I
)


class ReactionIntent(BaseModel):
    """Extracted intent for a spoken reaction interrupt or ready action."""

    is_reaction: bool = True
    action_type: str = "reaction"
    reaction_type: str = "custom"
    trigger_phrase: str
    target: str | None = None
    readied_action: str | None = None
    trigger_condition: str | None = None
    trigger_type: str | None = None
    confidence: float = 0.95
    speaker_name: str = ""
    raw_transcript: str
    parameters: dict[str, Any] = Field(default_factory=dict)


def _classify_trigger(cond: str) -> str:
    c = cond.lower()
    if any(k in c for k in ("step", "move", "walk", "enter", "approach", "run")):
        return "enemy_enters_range"
    if any(k in c for k in ("cast", "spell", "channel")):
        return "spell_cast"
    return (
        "attack" if any(k in c for k in ("attack", "strike", "shoot", "slash", "hit")) else "custom"
    )


def _spell_rx(
    t: str, spk: str, kind: str, target: str | None = None, **params: Any
) -> ReactionIntent:
    p = {"action": f"cast_{kind}", **params}
    if target:
        p["target"] = target
    return ReactionIntent(
        reaction_type=kind,
        trigger_phrase=t,
        target=target,
        speaker_name=spk,
        raw_transcript=t,
        parameters=p,
    )


def parse_reaction_intent(transcript: str, speaker_name: str = "") -> ReactionIntent | None:
    """Parse spoken reaction triggers and conditional ready actions from player speech."""
    t = transcript.strip()
    if not t:
        return None
    if m := _READY.search(t):
        act, cond = m.group(1).strip(), m.group(2).strip()
        tt = _classify_trigger(cond)
        return ReactionIntent(
            action_type="ready_action",
            reaction_type="ready_action",
            trigger_phrase=t,
            readied_action=act,
            trigger_condition=cond,
            trigger_type=tt,
            speaker_name=speaker_name,
            raw_transcript=t,
            parameters={"readied_action": act, "condition": cond, "trigger_type": tt},
        )
    if m := _OPP_ATK.search(t):
        tgt = m.group(1).strip() if m.group(1) else None
        p = {"action": "opportunity_attack"}
        if tgt:
            p["target"] = tgt
        return ReactionIntent(
            reaction_type="opportunity_attack",
            trigger_phrase=t,
            target=tgt,
            speaker_name=speaker_name,
            raw_transcript=t,
            parameters=p,
        )
    if _SHIELD.search(t):
        return _spell_rx(t, speaker_name, "shield", spell="Shield", ac_bonus=5)
    if _COUNTER.search(t):
        return _spell_rx(t, speaker_name, "counterspell", spell="Counterspell")
    if _ABSORB.search(t):
        return _spell_rx(t, speaker_name, "absorb_elements", spell="Absorb Elements")
    if m := _HELLISH.search(t):
        return _spell_rx(
            t, speaker_name, "hellish_rebuke", m.group(1).strip() if m.group(1) else None
        )
    if m := _SILVERY.search(t):
        return _spell_rx(
            t, speaker_name, "silvery_barbs", m.group(1).strip() if m.group(1) else None
        )
    if m := _DEFENSE.search(t):
        kind = m.group(1).lower().replace(" ", "_")
        return ReactionIntent(
            reaction_type=kind,
            trigger_phrase=t,
            speaker_name=speaker_name,
            raw_transcript=t,
            parameters={"action": kind},
        )
    return None
