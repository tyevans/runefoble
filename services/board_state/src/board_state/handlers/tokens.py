"""Token placement, kinematics, and hazards handler mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from board_state.handlers.actions import ActionsHandlerMixin
from board_state.models import MoveResult, PlacedTokenState
from board_state.rules import (
    calc_move_cost,
    calc_move_path,
    detect_path_hazards,
    is_within_bounds,
    validate_point_within_bounds,
)
from eventsource.domain.decorators import handles
from runefoble_events import events as ev

if TYPE_CHECKING:
    from board_state.models import BoardState


class TokensHandlerMixin(ActionsHandlerMixin):
    """Mixin providing token placement, movement kinematics, and path hazard triggers."""

    _state: BoardState | None
    state: BoardState
    aggregate_id: Any
    create_event: Any
    get_terrain: Any
    _sync_revealed_fog: Any

    def _get_token(self, token_id: str) -> tuple[str, Any]:
        tid = str(token_id)
        if tid not in self.state.tokens:
            raise ValueError(f"Token '{token_id}' not found on grid")
        return tid, self.state.tokens[tid]

    def place_token(
        self,
        token_id: str,
        name: str,
        token_type: Literal["pc", "monster", "npc", "obstacle"],
        x: int,
        y: int,
        hp: int | None = None,
        is_friendly: bool = False,
        vision_radius: int = 2,
    ) -> None:
        """Place a token onto the grid with spatial bounds check and fog update."""
        validate_point_within_bounds(x, y, self.state.cols, self.state.rows, "Placement")
        self.create_event(
            ev.TokenPlaced,
            session_id=self.aggregate_id,
            token_id=str(token_id),
            name=name,
            token_type=token_type,
            x=x,
            y=y,
            hp=hp,
            is_friendly=is_friendly,
        )
        if is_friendly and self.state.fog_of_war_enabled:
            self._sync_revealed_fog(str(token_id), x, y, vision_radius)

    def calculate_movement_path(
        self, from_x: int, from_y: int, to_x: int, to_y: int
    ) -> list[tuple[int, int]]:
        return calc_move_path(from_x, from_y, to_x, to_y)

    def calculate_movement_cost(self, path: list[tuple[int, int]]) -> int:
        return calc_move_cost(path, self.get_terrain)

    def move_token(
        self,
        token_id: str,
        to_x: int,
        to_y: int,
        initiated_by: Literal["player", "the_watcher", "stand_in"] = "player",
        movement_budget: int | None = None,
    ) -> MoveResult:
        """Move a placed token across the grid, evaluating traps and updating fog-of-war."""
        from board_state.traps.evaluator import evaluate_trap_collision_on_path

        tid, cur = self._get_token(token_id)
        if not is_within_bounds(to_x, to_y, self.state.cols, self.state.rows):
            raise ValueError(f"Target coordinates ({to_x}, {to_y}) out of bounds")

        full_path = self.calculate_movement_path(cur.x, cur.y, to_x, to_y)
        traps = getattr(self.state, "traps", {})
        breach = evaluate_trap_collision_on_path(full_path, traps)

        effective_to_x, effective_to_y = to_x, to_y
        effective_path = full_path
        trap_trig = None
        is_paused = False

        if breach is not None:
            effective_to_x, effective_to_y = breach.breach_coord
            effective_path = breach.effective_path
            trap_trig = breach.trap.trap_id
            is_paused = True

        cost = self.calculate_movement_cost(effective_path)
        if movement_budget is not None and cost > movement_budget:
            raise ValueError(f"Movement cost {cost} exceeds movement budget {movement_budget}")

        self.create_event(
            ev.TokenMoved,
            session_id=self.aggregate_id,
            token_id=tid,
            name=cur.name,
            from_x=cur.x,
            from_y=cur.y,
            to_x=effective_to_x,
            to_y=effective_to_y,
            initiated_by=initiated_by,
        )

        if breach is not None and hasattr(self, "spring_trap"):
            self.spring_trap(
                trap_id=breach.trap.trap_id,
                token_id=tid,
                trigger_type=breach.trap.trigger_type,
                x=effective_to_x,
                y=effective_to_y,
                damage_dice=breach.trap.damage_dice,
                effect_payload=breach.trap.effect_payload,
                movement_paused=True,
            )

        last_h, last_d = None, None
        for ht, dd in detect_path_hazards(effective_path, self.get_terrain):
            last_h, last_d = ht, dd
            self.create_event(
                ev.TokenHazardTriggered,
                session_id=str(self.state.session_id),
                board_id=str(self.aggregate_id),
                token_id=tid,
                hazard_type=ht,
                damage_dice=dd,
            )

        if cur.is_friendly and self.state.fog_of_war_enabled:
            self._sync_revealed_fog(tid, effective_to_x, effective_to_y, cur.vision_radius)
        return MoveResult(cost, last_h, last_d, trap_triggered=trap_trig, movement_paused=is_paused)

    def remove_token(self, token_id: str, reason: str = "defeated") -> None:
        """Remove a token from the board."""
        tid, _ = self._get_token(token_id)
        self.create_event(
            ev.TokenRemoved, session_id=self.aggregate_id, token_id=tid, reason=reason
        )

    @handles(ev.TokenHazardTriggered)
    def _on_hazard_triggered(self, e: ev.TokenHazardTriggered) -> None:
        self._state = self.state.with_hazard_triggered(str(e.token_id), e.hazard_type)

    @handles(ev.TokenPlaced)
    def _on_token_placed(self, e: ev.TokenPlaced) -> None:
        self._state = self.state.with_token_placed(
            PlacedTokenState.from_placed_event(e, self.get_terrain(e.x, e.y).hazard)
        )

    @handles(ev.TokenMoved)
    def _on_token_moved(self, e: ev.TokenMoved) -> None:
        self._state = self.state.with_token_moved(
            str(e.token_id), e.to_x, e.to_y, self.get_terrain(e.to_x, e.to_y).hazard
        )

    @handles(ev.TokenRemoved)
    def _on_token_removed(self, e: ev.TokenRemoved) -> None:
        self._state = self.state.without_token(str(e.token_id))
