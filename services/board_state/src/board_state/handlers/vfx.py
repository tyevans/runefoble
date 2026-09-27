"""Spell casting, AoE templates, VFX animations, and ephemeral decals handler mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from board_state.aoe_models import AoETemplateState
from board_state.spells import BoardSpellsMixin
from eventsource.domain.decorators import handles
from runefoble_events.events import (
    AoETemplatePlaced,
    AoETemplateRemoved,
    AreaEffectExploded,
    EphemeralDecalsDecayed,
    SpellCast,
    VFXAnimationFinished,
)

if TYPE_CHECKING:
    from board_state.models import BoardState


class VFXHandlerMixin(BoardSpellsMixin):
    """Mixin providing AoE templates, spell casting, particle VFX, and decal decay."""

    _state: BoardState | None
    state: BoardState
    aggregate_id: Any
    create_event: Any

    def place_aoe_template(
        self,
        template_id: str,
        shape: str,
        origin_x: float,
        origin_y: float,
        direction_deg: float = 0.0,
        radius_ft: float | None = None,
        length_ft: float | None = None,
        width_ft: float | None = 5.0,
        caster_token_id: str | None = None,
        spell_name: str | None = None,
        affected_token_ids: list[str] | None = None,
        affected_cells: list[list[int]] | None = None,
    ) -> None:
        """Place a geometric Area of Effect (AoE) spell template onto the board."""
        self.create_event(
            AoETemplatePlaced,
            session_id=str(self.state.session_id),
            board_id=str(self.aggregate_id),
            template_id=str(template_id),
            caster_token_id=str(caster_token_id) if caster_token_id else None,
            shape=shape,
            origin_x=float(origin_x),
            origin_y=float(origin_y),
            direction_deg=float(direction_deg),
            radius_ft=float(radius_ft) if radius_ft is not None else None,
            length_ft=float(length_ft) if length_ft is not None else None,
            width_ft=float(width_ft) if width_ft is not None else 5.0,
            spell_name=spell_name,
            affected_token_ids=affected_token_ids or [],
            affected_cells=affected_cells or [],
        )

    def remove_aoe_template(self, template_id: str) -> None:
        """Remove a placed AoE template from the board."""
        tid_str = str(template_id)
        if not any(t.template_id == tid_str for t in self.state.active_aoe_templates):
            raise ValueError(f"AoE template '{template_id}' not found on grid")
        self.create_event(
            AoETemplateRemoved,
            session_id=str(self.state.session_id),
            board_id=str(self.aggregate_id),
            template_id=tid_str,
        )

    @handles(AoETemplatePlaced)
    def _on_aoe_template_placed(self, event: AoETemplatePlaced) -> None:
        self._state = self.state.with_aoe_template_placed(
            AoETemplateState(
                template_id=event.template_id,
                caster_token_id=event.caster_token_id,
                shape=event.shape,
                origin_x=event.origin_x,
                origin_y=event.origin_y,
                direction_deg=event.direction_deg,
                radius_ft=event.radius_ft,
                length_ft=event.length_ft,
                width_ft=event.width_ft,
                spell_name=event.spell_name,
                affected_token_ids=event.affected_token_ids,
                affected_cells=event.affected_cells,
            )
        )

    @handles(AoETemplateRemoved)
    def _on_aoe_template_removed(self, event: AoETemplateRemoved) -> None:
        self._state = self.state.without_aoe_template(event.template_id)

    @handles(AreaEffectExploded)
    def _on_area_effect_exploded(self, event: AreaEffectExploded) -> None:
        self._state = self.state.with_area_effect(
            affected_cells=event.affected_cells,
            decal_type=event.decal_type,
            decal_duration_rounds=event.decal_duration_rounds,
        )

    @handles(SpellCast)
    def _on_spell_cast(self, event: SpellCast) -> None:
        pass

    @handles(VFXAnimationFinished)
    def _on_vfx_finished(self, event: VFXAnimationFinished) -> None:
        pass

    @handles(EphemeralDecalsDecayed)
    def _on_decals_decayed(self, event: EphemeralDecalsDecayed) -> None:
        self._state = self.state.with_decals_decayed(event.rounds)
