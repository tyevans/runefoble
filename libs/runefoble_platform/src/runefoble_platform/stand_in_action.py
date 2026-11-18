"""Stand-in action returned by The Watcher and read by game_session (ADR-0015 c).

game_session records this shape on the session aggregate. It reads the shape from the
shared contract, so it never imports The Watcher package.
"""

from pydantic import BaseModel, Field

from runefoble_platform.stand_in_guardrails import GuardrailName


class StandInAction(BaseModel):
    character_name: str
    action_type: str = "attack"
    action_description: str
    dialogue: str
    penalty_influence: str | None = None
    dice_roll_required: str | None = None
    penalties_applied: list[str] = Field(default_factory=list)
    guardrails_applied: list[GuardrailName] = Field(default_factory=list)
    flavor_text: str = ""
    source: str = "watcher_rules"  # "llm" | "heuristic" | "mock" from the worker
    degraded: bool = False
