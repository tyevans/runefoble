"""Fog-of-war revealing, shrouding, and party visibility calculations handler mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from board_state.rules import (
    calc_chebyshev,
    calc_party_vis,
    find_uncharted_cells,
    validate_cells_within_bounds,
)
from eventsource.domain.decorators import handles
from runefoble_events.events import FogOfWarRevealed, FogOfWarShrouded

if TYPE_CHECKING:
    from board_state.models import BoardState


class FogHandlerMixin:
    """Mixin providing fog-of-war revelation, shrouding, and visibility calculations."""

    _state: BoardState | None
    state: BoardState
    aggregate_id: Any
    create_event: Any

    def calculate_chebyshev_cells(self, cx: int, cy: int, radius: int) -> list[list[int]]:
        """Calculate all bounded grid coordinates within Chebyshev distance radius."""
        return calc_chebyshev(cx, cy, radius, self.state.cols, self.state.rows)

    def compute_party_visibility(self) -> list[list[int]]:
        """Compute the union of all cells currently visible by friendly/party tokens."""
        return calc_party_vis(self.state.tokens.values(), self.state.cols, self.state.rows)

    def _sync_revealed_fog(self, token_id: str, cx: int, cy: int, radius: int) -> None:
        """Evaluate newly seen cells and emit FogOfWarRevealed event if uncharted cells found."""
        new_cells = find_uncharted_cells(
            self.state.revealed_cells, self.calculate_chebyshev_cells(cx, cy, radius)
        )
        if new_cells:
            self.create_event(
                FogOfWarRevealed,
                session_id=self.aggregate_id,
                revealed_cells=new_cells,
                revealed_by_token_id=token_id,
            )

    def reveal_cells(self, cells: list[list[int]], revealed_by_token_id: str | None = None) -> None:
        """Manually reveal specified grid cells."""
        validate_cells_within_bounds(cells, self.state.cols, self.state.rows, "Reveal")
        self.create_event(
            FogOfWarRevealed,
            session_id=self.aggregate_id,
            revealed_cells=cells,
            revealed_by_token_id=revealed_by_token_id,
        )

    def shroud_cells(self, cells: list[list[int]]) -> None:
        """Manually shroud specified grid cells."""
        validate_cells_within_bounds(cells, self.state.cols, self.state.rows, "Shroud")
        self.create_event(
            FogOfWarShrouded,
            session_id=str(self.state.session_id),
            aggregate_id=self.aggregate_id,
            shrouded_cells=cells,
        )

    @handles(FogOfWarRevealed)
    def _on_fog_revealed(self, event: FogOfWarRevealed) -> None:
        self._state = self.state.with_fog_revealed(event.revealed_cells)

    @handles(FogOfWarShrouded)
    def _on_fog_shrouded(self, event: FogOfWarShrouded) -> None:
        self._state = self.state.with_fog_shrouded(event.shrouded_cells)
