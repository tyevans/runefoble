"""Pydantic wire models and state sanitization for OBS stream overlays."""

from __future__ import annotations

from typing import Any

from gateway_api.cinematic_director import CameraTarget
from pydantic import BaseModel, Field


class PartyMemberVitals(BaseModel):
    """Sanitized party member vitals for OBS stream HUD."""

    id: str
    name: str
    hp: int
    max_hp: int
    temp_hp: int = 0
    conditions: list[str] = Field(default_factory=list)
    is_ai_controlled: bool = False
    color: str | None = None
    is_active_turn: bool = False


class RollAnimationData(BaseModel):
    """Sanitized dice roll animation payload for OBS stream overlay."""

    id: str = "roll-1"
    roller_name: str
    dice_formula: str
    result: int
    is_critical: bool = False
    is_fumble: bool = False
    timestamp: str = ""


class PartyVitalsData(BaseModel):
    """Complete sanitized party vitals and camera state for stream overlay."""

    session_id: str
    party: list[PartyMemberVitals] = Field(default_factory=list)
    camera: CameraTarget = Field(default_factory=CameraTarget)
    recent_rolls: list[RollAnimationData] = Field(default_factory=list)
    round: int = 1
    position: str = "bottom"
    transparent: bool = True


def sanitize_party_vitals(
    raw_state: dict[str, Any],
    camera_target: CameraTarget | None = None,
    position: str = "bottom",
) -> PartyVitalsData:
    """Sanitize raw session state into safe spectator party vitals."""
    tokens = raw_state.get("tokens") or raw_state.get("board", {}).get("tokens") or []
    tok_list = list(tokens.values()) if isinstance(tokens, dict) else tokens

    members = [
        PartyMemberVitals(
            id=str(t.get("id", "")),
            name=str(t.get("name", "Adventurer")),
            hp=int(t.get("hp", 10)),
            max_hp=int(t.get("max_hp", 10)),
            temp_hp=int(t.get("temp_hp", 0)),
            conditions=[
                str(c if not isinstance(c, dict) else c.get("name", ""))
                for c in t.get("conditions", [])
            ]
            if isinstance(t.get("conditions"), list)
            else [],
            is_ai_controlled=bool(t.get("is_ai_controlled", False)),
            color=t.get("color"),
            is_active_turn=bool(t.get("is_active_turn", False)),
        )
        for tok in tok_list
        if (t := (tok if isinstance(tok, dict) else tok.model_dump()))
        and not any(t.get(k) for k in ("hidden", "is_secret", "is_hidden", "secret"))
        and not (
            "stat_block" in t
            or "cr" in t
            or t.get("is_enemy")
            or str(t.get("token_type", "")).lower() == "monster"
        )
    ]
    rolls = [
        RollAnimationData(
            id=str(r.get("id", "roll-1")),
            roller_name=str(r.get("roller_name", "Hero")),
            dice_formula=str(r.get("dice_formula", "1d20")),
            result=int(r.get("result", 0)),
            is_critical=bool(r.get("is_critical", False)),
            is_fumble=bool(r.get("is_fumble", False)),
            timestamp=str(r.get("timestamp", "")),
        )
        for r_raw in raw_state.get("recent_rolls", [])
        if not (r := (r_raw if isinstance(r_raw, dict) else r_raw.model_dump())).get("is_private")
        and not r.get("private")
    ]
    return PartyVitalsData(
        session_id=str(raw_state.get("session_id") or "session_default"),
        party=members,
        camera=camera_target or CameraTarget(),
        recent_rolls=rolls,
        round=int(raw_state.get("round", 1)),
        position=position,
        transparent=True,
    )


__all__ = [
    "PartyMemberVitals",
    "PartyVitalsData",
    "RollAnimationData",
    "sanitize_party_vitals",
]
