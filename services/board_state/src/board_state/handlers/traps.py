"""Secret DM spatial traps and battlemap stage switcher handler mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from board_state.traps.models import SecretTrapState
from eventsource.domain.decorators import handles
from runefoble_events import board_traps as bt

if TYPE_CHECKING:
    from board_state.models import BoardState


class TrapsHandlerMixin:
    """Mixin providing secret trap placement, proximity triggering, and map switching."""

    _state: BoardState | None
    state: BoardState
    aggregate_id: Any
    create_event: Any

    def place_trap(
        self,
        name: str = "Secret Trap",
        x: int = 0,
        y: int = 0,
        trigger_type: Literal["step", "proximity", "touch"] = "step",
        proximity_radius: int = 1,
        dc_detection: int = 15,
        trap_type: str = "pit_trap",
        is_secret: bool = True,
        damage_dice: str | None = None,
        description: str = "",
        effect_payload: dict[str, Any] | None = None,
        trap_id: str | None = None,
        created_by: str | None = None,
    ) -> str:
        """Place a secret DM trap on the tactical grid."""
        tid = trap_id or f"trap-{uuid4().hex[:8]}"
        self.create_event(
            bt.TrapPlacedEvent,
            session_id=self.aggregate_id,
            board_id=str(self.aggregate_id),
            trap_id=tid,
            name=name,
            x=x,
            y=y,
            trigger_type=trigger_type,
            proximity_radius=proximity_radius,
            dc_detection=dc_detection,
            trap_type=trap_type,
            is_secret=is_secret,
            damage_dice=damage_dice,
            description=description,
            effect_payload=effect_payload or {},
            created_by=created_by,
        )
        return tid

    def spring_trap(
        self,
        trap_id: str,
        token_id: str,
        trigger_type: Literal["step", "proximity", "touch"] = "step",
        x: int = 0,
        y: int = 0,
        damage_dice: str | None = None,
        effect_payload: dict[str, Any] | None = None,
        movement_paused: bool = True,
    ) -> None:
        """Spring an armed trap upon token breach and pause movement."""
        self.create_event(
            bt.TrapSprungEvent,
            session_id=self.aggregate_id,
            board_id=str(self.aggregate_id),
            trap_id=trap_id,
            token_id=str(token_id),
            trigger_type=trigger_type,
            x=x,
            y=y,
            damage_dice=damage_dice,
            effect_payload=effect_payload or {},
            movement_paused=movement_paused,
        )

    def disarm_trap(self, trap_id: str, disarmed_by: str | None = None) -> None:
        """Disarm an armed trap."""
        if trap_id not in self.state.traps:
            raise ValueError(f"Trap '{trap_id}' not found on grid")
        self.create_event(
            bt.TrapDisarmedEvent,
            session_id=self.aggregate_id,
            board_id=str(self.aggregate_id),
            trap_id=trap_id,
            disarmed_by=disarmed_by,
        )

    def switch_battlemap(
        self,
        new_map_id: str,
        cols: int,
        rows: int,
        background_asset_id: str | None = None,
        background_image_url: str | None = None,
        token_teleports: dict[str, list[int]] | None = None,
        initiated_by: str | None = None,
        clear_existing_traps: bool = False,
    ) -> None:
        """Transition board to new battlemap and teleport party tokens in a single transaction."""
        prev_map_id = getattr(self.state, "current_map_id", None)
        self.create_event(
            bt.BattlemapSwitchedEvent,
            session_id=self.aggregate_id,
            board_id=str(self.aggregate_id),
            previous_map_id=prev_map_id,
            new_map_id=new_map_id,
            cols=cols,
            rows=rows,
            background_asset_id=background_asset_id,
            background_image_url=background_image_url,
            teleported_tokens=token_teleports or {},
            initiated_by=initiated_by,
        )

    @handles(bt.TrapPlacedEvent)
    def _on_trap_placed(self, e: bt.TrapPlacedEvent) -> None:
        self._state = self.state.with_trap_placed(
            SecretTrapState(
                trap_id=e.trap_id,
                board_id=e.board_id,
                name=e.name,
                x=e.x,
                y=e.y,
                trigger_type=e.trigger_type,
                proximity_radius=e.proximity_radius,
                dc_detection=e.dc_detection,
                trap_type=e.trap_type,
                is_secret=e.is_secret,
                damage_dice=e.damage_dice,
                description=e.description,
                effect_payload=e.effect_payload,
                created_by=e.created_by,
            )
        )

    @handles(bt.TrapSprungEvent)
    def _on_trap_sprung(self, e: bt.TrapSprungEvent) -> None:
        self._state = self.state.with_trap_sprung(e.trap_id, e)

    @handles(bt.TrapDisarmedEvent)
    def _on_trap_disarmed(self, e: bt.TrapDisarmedEvent) -> None:
        self._state = self.state.with_trap_disarmed(e.trap_id)

    @handles(bt.BattlemapSwitchedEvent)
    def _on_battlemap_switched(self, e: bt.BattlemapSwitchedEvent) -> None:
        self._state = self.state.with_battlemap_switched(
            new_map_id=e.new_map_id,
            cols=e.cols,
            rows=e.rows,
            background_asset_id=e.background_asset_id,
            background_image_url=e.background_image_url,
            teleported_tokens=e.teleported_tokens,
        )
