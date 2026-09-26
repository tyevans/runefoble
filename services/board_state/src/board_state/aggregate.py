"""Event-sourced BoardState aggregate using eventsource-py."""

from typing import Literal
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import (
    BoardGridInitialized,
    TokenMoved,
    TokenPlaced,
    TokenRemoved,
)


class PlacedTokenState(BaseModel):
    token_id: str
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = False


class BoardState(BaseModel):
    board_id: UUID
    session_id: str = ""
    cols: int = 12
    rows: int = 12
    tokens: dict[str, PlacedTokenState] = Field(default_factory=dict)


class BoardAggregate(DeclarativeAggregate[BoardState]):
    """Event-sourced aggregate managing tactical combat grid and spatial tokens."""

    aggregate_type = "BoardState"
    requires_creation_event = True

    def initialize_grid(self, cols: int = 12, rows: int = 12, session_id: str = "") -> None:
        """Initialize new tactical grid dimensions."""
        self.create_event(
            BoardGridInitialized,
            session_id=self.aggregate_id,
            width=cols,
            height=rows,
            session_id_str=session_id,
        )

    def place_token(
        self,
        token_id: str,
        name: str,
        token_type: Literal["pc", "monster", "npc", "obstacle"],
        x: int,
        y: int,
        hp: int | None = None,
        is_friendly: bool = False,
    ) -> None:
        """Place a token onto the grid with spatial bounds check."""
        if not (0 <= x < self.state.cols and 0 <= y < self.state.rows):
            raise ValueError(f"Placement coordinates ({x}, {y}) out of grid bounds")

        self.create_event(
            TokenPlaced,
            session_id=self.aggregate_id,
            token_id=str(token_id),
            name=name,
            token_type=token_type,
            x=x,
            y=y,
            hp=hp,
            is_friendly=is_friendly,
        )

    def move_token(
        self,
        token_id: str,
        to_x: int,
        to_y: int,
        initiated_by: Literal["player", "the_watcher", "stand_in"] = "player",
    ) -> None:
        """Move a placed token across the grid."""
        tid_str = str(token_id)
        if tid_str not in self.state.tokens:
            raise ValueError(f"Token '{token_id}' not found on grid")

        if not (0 <= to_x < self.state.cols and 0 <= to_y < self.state.rows):
            raise ValueError(f"Target coordinates ({to_x}, {to_y}) out of bounds")

        current = self.state.tokens[tid_str]
        self.create_event(
            TokenMoved,
            session_id=self.aggregate_id,
            token_id=tid_str,
            name=current.name,
            from_x=current.x,
            from_y=current.y,
            to_x=to_x,
            to_y=to_y,
            initiated_by=initiated_by,
        )

    def remove_token(self, token_id: str, reason: str = "defeated") -> None:
        """Remove a token from the board."""
        tid_str = str(token_id)
        if tid_str not in self.state.tokens:
            raise ValueError(f"Token '{token_id}' not found on grid")

        self.create_event(
            TokenRemoved,
            session_id=self.aggregate_id,
            token_id=tid_str,
            reason=reason,
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(BoardGridInitialized)
    def _on_grid_initialized(self, event: BoardGridInitialized) -> None:
        self._state = BoardState(
            board_id=event.aggregate_id,
            session_id=event.session_id_str or str(event.aggregate_id),
            cols=event.width,
            rows=event.height,
        )

    @handles(TokenPlaced)
    def _on_token_placed(self, event: TokenPlaced) -> None:
        tokens = dict(self.state.tokens)
        tokens[str(event.token_id)] = PlacedTokenState(
            token_id=str(event.token_id),
            name=event.name,
            token_type=event.token_type,
            x=event.x,
            y=event.y,
            hp=event.hp,
            is_friendly=event.is_friendly,
        )
        self._state = self.state.model_copy(update={"tokens": tokens})

    @handles(TokenMoved)
    def _on_token_moved(self, event: TokenMoved) -> None:
        tokens = dict(self.state.tokens)
        tid_str = str(event.token_id)
        if tid_str in tokens:
            tokens[tid_str] = tokens[tid_str].model_copy(update={"x": event.to_x, "y": event.to_y})
        self._state = self.state.model_copy(update={"tokens": tokens})

    @handles(TokenRemoved)
    def _on_token_removed(self, event: TokenRemoved) -> None:
        tokens = dict(self.state.tokens)
        tokens.pop(str(event.token_id), None)
        self._state = self.state.model_copy(update={"tokens": tokens})
