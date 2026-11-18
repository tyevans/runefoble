"""Shared request contract for missing player stand-in tactical guardrails.

The Watcher owns the policy. The inference worker applies it. Both services validate the
same model, so an unknown or misspelled guardrail name fails with a 422 at each boundary.

This model holds the only default policy. A field that the request omits takes the default
shown on that field. The character sheet stores this model, so a character with no stored
policy uses the same defaults. The contract test in
`tests/test_blackbox_stand_in_guardrail_contract.py` checks the field names.

`GuardrailName` is the only set of names that an engine may report in `guardrails_applied`.
It lists the guardrails that the engines enforce. Policy fields outside this set are stored
but not enforced by a stand-in engine yet.
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GuardrailName(StrEnum):
    """A guardrail that a stand-in engine enforces and reports by name."""

    PRESERVE_SPELL_SLOTS = "preserve_spell_slots"
    PROTECT_ALLIES = "protect_allies"
    AVOID_MELEE = "avoid_melee"
    CUSTOM_PRIORITIES = "custom_priorities"


class StandInGuardrailPolicy(BaseModel):
    """Tactical guardrails for an absent player's character. Unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid")

    preserve_spell_slots: dict[int, int] = Field(
        default_factory=dict,
        description="Spell level to slots held in reserve",
    )
    protect_allies: list[str] = Field(
        default_factory=list,
        description="Ally names the stand-in must protect when they are in the scene",
    )
    protect_ally_hp_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    risk_threshold: Literal["cautious", "balanced", "reckless"] = "cautious"
    avoid_melee: bool = True
    permadeath_safeguard: bool = True
    custom_priorities: list[str] = Field(default_factory=list)
