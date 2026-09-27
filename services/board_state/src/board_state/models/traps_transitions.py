"""Board aggregate state transitions for secret DM traps and map switching."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from board_state.models.board import BoardState


class BoardTrapsTransitionsMixin:
    """Provides pure state mutation helpers for secret traps and map switching."""

    def with_trap_placed(self: BoardState, trap: Any) -> BoardState:
        traps = dict(self.traps)
        traps[str(trap.trap_id)] = trap
        return self.model_copy(update={"traps": traps})

    def with_trap_sprung(self: BoardState, trap_id: str, event: Any) -> BoardState:
        traps = dict(self.traps)
        tid = str(trap_id)
        if tid in traps:
            t = traps[tid]
            traps[tid] = t.model_copy(update={"is_sprung": True, "is_armed": False})
        return self.model_copy(update={"traps": traps, "last_trap_sprung": event})

    def with_trap_disarmed(self: BoardState, trap_id: str) -> BoardState:
        traps = dict(self.traps)
        tid = str(trap_id)
        if tid in traps:
            t = traps[tid]
            traps[tid] = t.model_copy(update={"is_disarmed": True, "is_armed": False})
        return self.model_copy(update={"traps": traps})

    def with_battlemap_switched(
        self: BoardState,
        new_map_id: str,
        cols: int,
        rows: int,
        background_asset_id: str | None = None,
        background_image_url: str | None = None,
        teleported_tokens: dict[str, list[int]] | None = None,
    ) -> BoardState:
        tokens = dict(self.tokens)
        if teleported_tokens:
            for tid, coords in teleported_tokens.items():
                if tid in tokens and len(coords) >= 2:
                    tokens[tid] = tokens[tid].model_copy(update={"x": coords[0], "y": coords[1]})
        return self.model_copy(
            update={
                "current_map_id": new_map_id,
                "cols": cols,
                "rows": rows,
                "background_asset_id": background_asset_id,
                "background_image_url": background_image_url,
                "tokens": tokens,
            }
        )
