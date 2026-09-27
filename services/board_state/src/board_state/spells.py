"""Spell casting and WebGL VFX particle effects mixin for BoardAggregate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from board_state.rules import (
    calc_move_path,
    compute_spell_vfx_impact,
    validate_point_within_bounds,
)
from runefoble_events.events import (
    AreaEffectExploded,
    EphemeralDecalsDecayed,
    SpellCast,
    VFXAnimationFinished,
)

if TYPE_CHECKING:
    from board_state.models import BoardState


class BoardSpellsMixin:
    """Mixin providing spell casting, VFX particle tracking, and decal decay for BoardAggregate."""

    state: BoardState
    aggregate_id: Any
    create_event: Any

    def cast_spell(
        self,
        spell_name: str,
        target_x: int,
        target_y: int,
        caster_token_id: str | None = None,
        spell_archetype: str = "evocation",
        origin_x: int | None = None,
        origin_y: int | None = None,
        radius_ft: int = 20,
        damage_dice: str | None = None,
        damage_type: str | None = None,
        theme_palette: str | None = None,
    ) -> tuple[str, list[list[float]], list[str], list[list[int]], str | None]:
        """Cast kinetic spell, calculate trajectory, radius bloom, affected tokens, and decals."""
        validate_point_within_bounds(
            target_x, target_y, self.state.cols, self.state.rows, "Spell target"
        )

        ox, oy = origin_x, origin_y
        if ox is None or oy is None:
            if caster_token_id and caster_token_id in self.state.tokens:
                caster = self.state.tokens[caster_token_id]
                ox, oy = caster.x, caster.y
            else:
                ox, oy = target_x, target_y

        self.create_event(
            SpellCast,
            session_id=str(self.state.session_id),
            board_id=str(self.aggregate_id),
            caster_token_id=caster_token_id,
            spell_name=spell_name,
            spell_archetype=spell_archetype,
            target_x=target_x,
            target_y=target_y,
            origin_x=ox,
            origin_y=oy,
            radius_ft=radius_ft,
            damage_dice=damage_dice,
            damage_type=damage_type,
            theme_palette=theme_palette,
        )

        path = calc_move_path(ox, oy, target_x, target_y)
        trajectory = [[float(ox), float(oy)]] + [[float(p[0]), float(p[1])] for p in path]

        affected_cells, affected_token_ids, decal_type = compute_spell_vfx_impact(
            target_x=target_x,
            target_y=target_y,
            cols=self.state.cols,
            rows=self.state.rows,
            tokens=self.state.tokens,
            radius_ft=radius_ft,
            spell_name=spell_name,
            spell_archetype=spell_archetype,
            damage_type=damage_type,
        )

        if affected_cells:
            self.create_event(
                AreaEffectExploded,
                session_id=str(self.state.session_id),
                board_id=str(self.aggregate_id),
                spell_name=spell_name,
                center_x=target_x,
                center_y=target_y,
                radius_ft=radius_ft,
                affected_token_ids=affected_token_ids,
                affected_cells=affected_cells,
                decal_type=decal_type,
                decal_duration_rounds=2,
            )

        animation_id = f"vfx-{uuid4().hex[:8]}"
        return animation_id, trajectory, affected_token_ids, affected_cells, decal_type

    def finish_vfx(
        self,
        animation_id: str,
        spell_name: str,
        target_x: int,
        target_y: int,
        duration_ms: int = 500,
    ) -> None:
        """Mark WebGL particle VFX animation complete."""
        self.create_event(
            VFXAnimationFinished,
            session_id=str(self.state.session_id),
            board_id=str(self.aggregate_id),
            animation_id=animation_id,
            spell_name=spell_name,
            target_x=target_x,
            target_y=target_y,
            duration_ms=duration_ms,
        )

    def decay_decals(self, rounds: int = 1) -> None:
        """Decay ephemeral decals on the tactical board."""
        self.create_event(
            EphemeralDecalsDecayed,
            session_id=str(self.state.session_id),
            board_id=str(self.aggregate_id),
            rounds=rounds,
        )
