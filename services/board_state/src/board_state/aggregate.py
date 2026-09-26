"""Event-sourced BoardState aggregate using eventsource-py."""

from typing import Literal

from board_state.models import (
    BoardState,
    PlacedTokenState,
    TerrainCellState,
    TerrainDict,
)
from board_state.rules import (
    DEFAULT_HAZARD_DAMAGE,
    calc_chebyshev,
    calc_move_cost,
    calc_move_path,
    calc_party_vis,
    detect_path_hazards,
    find_uncharted_cells,
    get_hazard_damage_dice,
    is_within_bounds,
    validate_cells_within_bounds,
    validate_point_within_bounds,
)
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from runefoble_events.events import (
    BoardGridInitialized,
    FogOfWarRevealed,
    FogOfWarShrouded,
    TerrainCellModified,
    TokenHazardTriggered,
    TokenMoved,
    TokenPlaced,
    TokenRemoved,
)

__all__ = [
    "DEFAULT_HAZARD_DAMAGE",
    "BoardAggregate",
    "BoardState",
    "PlacedTokenState",
    "TerrainCellState",
    "TerrainDict",
    "get_hazard_damage_dice",
]


class BoardAggregate(DeclarativeAggregate[BoardState]):
    """Event-sourced aggregate managing tactical combat grid, spatial tokens, and fog-of-war."""

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
        if is_friendly and self.state.fog_of_war_enabled:
            self._sync_revealed_fog(str(token_id), x, y, vision_radius)

    def configure_terrain(
        self,
        x: int,
        y: int,
        elevation: int = 0,
        terrain_type: str = "normal",
        hazard: str | None = None,
    ) -> None:
        """Configure terrain properties of a cell on the board."""
        validate_point_within_bounds(x, y, self.state.cols, self.state.rows, "Terrain")
        self.create_event(
            TerrainCellModified,
            session_id=str(self.state.session_id),
            board_id=str(self.aggregate_id),
            x=x,
            y=y,
            elevation=elevation,
            terrain_type=terrain_type,
            hazard=hazard,
        )

    def get_terrain(self, x: int, y: int) -> TerrainCellState:
        """Get terrain metadata for cell (x, y), defaulting to normal elevation 0."""
        cell = self.state.terrain_cells.get((x, y))
        return cell if cell is not None else TerrainCellState(x=x, y=y)

    def calculate_movement_path(
        self, from_x: int, from_y: int, to_x: int, to_y: int
    ) -> list[tuple[int, int]]:
        """Calculate line of cells traversed when moving between coordinates."""
        return calc_move_path(from_x, from_y, to_x, to_y)

    def calculate_movement_cost(self, path: list[tuple[int, int]]) -> int:
        """Calculate movement budget cost across path, difficult terrain costs 2x per cell."""
        return calc_move_cost(path, self.get_terrain)

    def move_token(
        self,
        token_id: str,
        to_x: int,
        to_y: int,
        initiated_by: Literal["player", "the_watcher", "stand_in"] = "player",
        movement_budget: int | None = None,
    ) -> tuple[int, str | None, str | None]:
        """Move a placed token across the grid and update revealed fog-of-war."""
        tid_str = str(token_id)
        if tid_str not in self.state.tokens:
            raise ValueError(f"Token '{token_id}' not found on grid")
        if not is_within_bounds(to_x, to_y, self.state.cols, self.state.rows):
            raise ValueError(f"Target coordinates ({to_x}, {to_y}) out of bounds")

        current = self.state.tokens[tid_str]
        path = self.calculate_movement_path(current.x, current.y, to_x, to_y)
        cost = self.calculate_movement_cost(path)
        if movement_budget is not None and cost > movement_budget:
            raise ValueError(f"Movement cost {cost} exceeds movement budget {movement_budget}")

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

        hazards = detect_path_hazards(path, self.get_terrain)
        last_hazard, last_damage = None, None
        for h_type, d_dice in hazards:
            last_hazard, last_damage = h_type, d_dice
            self.create_event(
                TokenHazardTriggered,
                session_id=str(self.state.session_id),
                board_id=str(self.aggregate_id),
                token_id=tid_str,
                hazard_type=h_type,
                damage_dice=d_dice,
            )

        if current.is_friendly and self.state.fog_of_war_enabled:
            self._sync_revealed_fog(tid_str, to_x, to_y, current.vision_radius)
        return cost, last_hazard, last_damage

    def remove_token(self, token_id: str, reason: str = "defeated") -> None:
        """Remove a token from the board."""
        tid_str = str(token_id)
        if tid_str not in self.state.tokens:
            raise ValueError(f"Token '{token_id}' not found on grid")
        self.create_event(
            TokenRemoved, session_id=self.aggregate_id, token_id=tid_str, reason=reason
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

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(BoardGridInitialized)
    def _on_grid_initialized(self, event: BoardGridInitialized) -> None:
        self._state = BoardState.initial(
            event.aggregate_id,
            event.session_id_str or str(event.aggregate_id),
            event.width,
            event.height,
        )

    @handles(TerrainCellModified)
    def _on_terrain_modified(self, event: TerrainCellModified) -> None:
        self._state = self.state.with_terrain_modified_from_event(event)

    @handles(TokenHazardTriggered)
    def _on_hazard_triggered(self, event: TokenHazardTriggered) -> None:
        self._state = self.state.with_hazard_triggered(
            token_id=str(event.token_id), hazard_type=event.hazard_type
        )

    @handles(TokenPlaced)
    def _on_token_placed(self, event: TokenPlaced) -> None:
        h = self.get_terrain(event.x, event.y).hazard
        self._state = self.state.with_token_placed(PlacedTokenState.from_placed_event(event, h))

    @handles(TokenMoved)
    def _on_token_moved(self, event: TokenMoved) -> None:
        h = self.get_terrain(event.to_x, event.to_y).hazard
        self._state = self.state.with_token_moved(
            token_id=str(event.token_id), to_x=event.to_x, to_y=event.to_y, active_hazard=h
        )

    @handles(TokenRemoved)
    def _on_token_removed(self, event: TokenRemoved) -> None:
        self._state = self.state.without_token(str(event.token_id))

    @handles(FogOfWarRevealed)
    def _on_fog_revealed(self, event: FogOfWarRevealed) -> None:
        self._state = self.state.with_fog_revealed(event.revealed_cells)

    @handles(FogOfWarShrouded)
    def _on_fog_shrouded(self, event: FogOfWarShrouded) -> None:
        self._state = self.state.with_fog_shrouded(event.shrouded_cells)
