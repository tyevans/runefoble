"""Kinetic spell VFX, area-of-effect bloom, and decal decay domain events."""

from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.board.spell_cast")
class SpellCast(BaseRunefobleEvent):
    """Emitted when a kinetic spell is cast on the tactical board."""

    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.spell_cast"
    session_id: str = ""
    board_id: str = ""
    caster_token_id: str | None = None
    spell_name: str
    spell_archetype: str = "evocation"
    target_x: int
    target_y: int
    origin_x: int | None = None
    origin_y: int | None = None
    radius_ft: int = 20
    damage_dice: str | None = None
    damage_type: str | None = None
    theme_palette: str | None = None


@register_event("runefoble.events.board.area_effect_exploded")
class AreaEffectExploded(BaseRunefobleEvent):
    """Emitted when an area-of-effect spell blooms across grid cells."""

    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.area_effect_exploded"
    session_id: str = ""
    board_id: str = ""
    spell_name: str
    center_x: int
    center_y: int
    radius_ft: int = 20
    affected_token_ids: list[str] = Field(default_factory=list)
    affected_cells: list[list[int]] = Field(default_factory=list)
    decal_type: str | None = "scorched_earth"
    decal_duration_rounds: int = 2


@register_event("runefoble.events.board.vfx_animation_finished")
class VFXAnimationFinished(BaseRunefobleEvent):
    """Emitted when a WebGL particle animation completes its playback."""

    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.vfx_animation_finished"
    session_id: str = ""
    board_id: str = ""
    animation_id: str
    spell_name: str
    target_x: int
    target_y: int
    duration_ms: int = 500


@register_event("runefoble.events.board.decals_decayed")
class EphemeralDecalsDecayed(BaseRunefobleEvent):
    """Emitted when ephemeral decals on the board decay across rounds."""

    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.decals_decayed"
    session_id: str = ""
    board_id: str = ""
    rounds: int = 1
