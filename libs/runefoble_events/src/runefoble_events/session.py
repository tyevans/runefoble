"""GameSession aggregate and spectator stream events."""

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.session.created")
class SessionCreated(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.created"

    aggregate_type: str = "GameSession"
    title: str = "Untitled Session"
    dm_id: str = "the_watcher"
    campaign_id: UUID | str = ""
    session_id: UUID | str = ""
    created_by: str = "system"


@register_event("runefoble.events.session.started")
class SessionStarted(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.started"

    aggregate_type: str = "GameSession"
    started_at_turn: int = 1


@register_event("runefoble.events.session.player_joined_session")
class PlayerJoinedSession(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.player_joined_session"

    aggregate_type: str = "GameSession"
    player_id: str
    character_id: UUID
    character_name: str
    character_class: str


@register_event("runefoble.events.session.player_left_session")
class PlayerLeftSession(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.player_left_session"

    aggregate_type: str = "GameSession"
    player_id: str
    reason: str = "disconnected"


@register_event("runefoble.events.session.turn_advanced")
class TurnAdvanced(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.turn_advanced"

    aggregate_type: str = "GameSession"
    previous_turn: int
    new_turn: int
    active_character_id: UUID | None = None


@register_event("runefoble.events.session.turn_started")
class TurnStarted(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.turn_started"

    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    session_id: UUID | str = ""
    turn_number: int = 1
    character_id: UUID | str = ""
    character_name: str = ""
    token_id: str | None = None


@register_event("runefoble.events.session.ended")
class SessionEnded(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.ended"

    aggregate_type: str = "GameSession"
    summary: str = "Session completed"


@register_event("runefoble.events.session.combat_encounter_started")
class CombatEncounterStarted(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.combat_encounter_started"

    aggregate_type: str = "GameSession"
    session_id: UUID | str | None = None
    round_number: int = 1
    combatants: list[dict[str, Any]] = Field(default_factory=list)
    # The encounter board and the tokens to place on it. board_state consumes these (TASK-0749).
    # An empty `placements` means combat only, with no board work.
    board_cols: int | None = None
    board_rows: int | None = None
    placements: list[dict[str, Any]] = Field(default_factory=list)
    initiated_by: str = ""


@register_event("runefoble.events.session.initiative_rolled")
class InitiativeRolled(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.initiative_rolled"

    aggregate_type: str = "GameSession"
    session_id: UUID | str | None = None
    combatant_id: str
    combatant_name: str
    initiative_score: float | int
    is_npc: bool = False


@register_event("runefoble.events.session.initiative_turn_advanced")
class InitiativeTurnAdvanced(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.initiative_turn_advanced"

    aggregate_type: str = "GameSession"
    session_id: UUID | str | None = None
    round_number: int
    active_combatant_id: str
    turn_seconds_remaining: int = 60


@register_event("runefoble.events.session.combat_round_advanced")
class CombatRoundAdvanced(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.combat_round_advanced"

    aggregate_type: str = "GameSession"
    session_id: UUID | str | None = None
    round_number: int
    active_combatant_id: str = ""


@register_event("runefoble.events.session.combat_encounter_ended")
class CombatEncounterEnded(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.combat_encounter_ended"

    aggregate_type: str = "GameSession"
    session_id: UUID | str | None = None
    total_rounds: int


@register_event("runefoble.events.session.readiness_toggled")
class ReadinessToggled(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.readiness_toggled"

    aggregate_type: str = "GameSession"
    session_id: UUID | str = ""
    player_id: str
    is_ready: bool


@register_event("runefoble.events.session.character_selected_for_lobby")
class CharacterSelectedForLobby(BaseRunefobleEvent):
    event_type: str = "runefoble.events.session.character_selected_for_lobby"

    aggregate_type: str = "GameSession"
    session_id: UUID | str = ""
    player_id: str
    character_id: UUID


@register_event("runefoble.events.session.character_control_transferred")
class CharacterControlTransferred(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    event_type: str = "runefoble.events.session.character_control_transferred"
    session_id: UUID | str
    character_id: UUID | str
    player_id: str
    previous_controller: str = "ai_stand_in"
    new_controller: str = "player"


@register_event("runefoble.events.session.dm_override_applied")
class DMOverrideApplied(BaseRunefobleEvent):
    """The DM applied an override to the live session (TASK-0581)."""

    aggregate_type: str = "GameSession"
    event_type: str = "runefoble.events.session.dm_override_applied"
    action: str
    reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.session.atmosphere_updated")
class AtmosphereUpdated(BaseRunefobleEvent):
    """The DM changed the location, lighting, and mood of the session (TASK-0581)."""

    aggregate_type: str = "GameSession"
    event_type: str = "runefoble.events.session.atmosphere_updated"
    location_name: str
    lighting: str = "Normal"
    mood: str = "Neutral"
    description: str = ""
    ambient_audio_prompt: str | None = None


@register_event("runefoble.events.session.weather_changed")
class WeatherChanged(BaseRunefobleEvent):
    """The session weather changed because an approved audience modifier applied (TASK-0441)."""

    aggregate_type: str = "GameSession"
    event_type: str = "runefoble.events.session.weather_changed"
    weather: str
    source_proposal_id: UUID | str | None = None
