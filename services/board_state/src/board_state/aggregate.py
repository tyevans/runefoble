"""Event-sourced BoardState aggregate using eventsource-py."""

from typing import Literal
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
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

DEFAULT_HAZARD_DAMAGE: dict[str, str] = {
    "lava": "2d10",
    "fire": "1d6",
    "acid": "2d6",
    "spikes": "2d4",
    "poison": "1d4",
}


class TerrainCellState(BaseModel):
    x: int
    y: int
    elevation: int = 0
    terrain_type: str = "normal"
    hazard: str | None = None
    hazard_status: str | None = None


class TerrainDict(dict):
    """Dictionary supporting both 'x,y' string keys and (x, y) tuple keys."""

    def __getitem__(self, key):
        if isinstance(key, tuple):
            return super().__getitem__(f"{key[0]},{key[1]}")
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            super().__setitem__(f"{key[0]},{key[1]}", value)
        else:
            super().__setitem__(key, value)

    def __contains__(self, key):
        if isinstance(key, tuple):
            return super().__contains__(f"{key[0]},{key[1]}")
        return super().__contains__(key)

    def get(self, key, default=None):
        if isinstance(key, tuple):
            return super().get(f"{key[0]},{key[1]}", default)
        return super().get(key, default)


class PlacedTokenState(BaseModel):
    token_id: str
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = False
    vision_radius: int = 2
    active_hazard: str | None = None
    hazard_status: str | None = None


class BoardState(BaseModel):
    board_id: UUID
    session_id: str = ""
    cols: int = 12
    rows: int = 12
    tokens: dict[str, PlacedTokenState] = Field(default_factory=dict)
    terrain_cells: dict[str, TerrainCellState] = Field(default_factory=TerrainDict)
    active_hazards: list[str] = Field(default_factory=list)
    fog_of_war_enabled: bool = True
    revealed_cells: list[list[int]] = Field(default_factory=list)


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
        cells: list[list[int]] = []
        min_x = max(0, cx - radius)
        max_x = min(self.state.cols - 1, cx + radius)
        min_y = max(0, cy - radius)
        max_y = min(self.state.rows - 1, cy + radius)

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                cells.append([x, y])
        return cells

    def compute_party_visibility(self) -> list[list[int]]:
        """Compute the union of all cells currently visible by friendly/party tokens."""
        seen: set[tuple[int, int]] = set()
        for token in self.state.tokens.values():
            if token.is_friendly:
                for c in self.calculate_chebyshev_cells(token.x, token.y, token.vision_radius):
                    seen.add((c[0], c[1]))
        return [list(c) for c in sorted(seen)]

    def _sync_revealed_fog(self, token_id: str, cx: int, cy: int, radius: int) -> None:
        """Evaluate newly seen cells and emit FogOfWarRevealed event if uncharted cells found."""
        existing_revealed = {tuple(c) for c in self.state.revealed_cells}
        token_cells = self.calculate_chebyshev_cells(cx, cy, radius)
        new_cells = [c for c in token_cells if tuple(c) not in existing_revealed]

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
        if not (0 <= x < self.state.cols and 0 <= y < self.state.rows):
            raise ValueError(f"Terrain coordinates ({x}, {y}) out of grid bounds")

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
        if cell is not None:
            return cell
        return TerrainCellState(x=x, y=y, elevation=0, terrain_type="normal", hazard=None)

    def calculate_movement_path(
        self, from_x: int, from_y: int, to_x: int, to_y: int
    ) -> list[tuple[int, int]]:
        """Calculate line of cells traversed when moving between coordinates."""
        dx = to_x - from_x
        dy = to_y - from_y
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return []
        path: list[tuple[int, int]] = []
        for step in range(1, steps + 1):
            cx = round(from_x + step * (dx / steps))
            cy = round(from_y + step * (dy / steps))
            path.append((int(cx), int(cy)))
        return path

    def calculate_movement_cost(self, path: list[tuple[int, int]]) -> int:
        """Calculate movement budget cost across path, difficult terrain costs 2x per cell."""
        cost = 0
        for cx, cy in path:
            terrain = self.get_terrain(cx, cy)
            if terrain.terrain_type == "difficult":
                cost += 2
            else:
                cost += 1
        return cost

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

        if not (0 <= to_x < self.state.cols and 0 <= to_y < self.state.rows):
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

        hazard_triggered: str | None = None
        damage_dice: str | None = None
        for cx, cy in path:
            cell_terrain = self.get_terrain(cx, cy)
            if cell_terrain.hazard:
                hazard_triggered = cell_terrain.hazard
                damage_dice = DEFAULT_HAZARD_DAMAGE.get(hazard_triggered, "1d6")
                self.create_event(
                    TokenHazardTriggered,
                    session_id=str(self.state.session_id),
                    board_id=str(self.aggregate_id),
                    token_id=tid_str,
                    hazard_type=hazard_triggered,
                    damage_dice=damage_dice,
                )

        if current.is_friendly and self.state.fog_of_war_enabled:
            self._sync_revealed_fog(tid_str, to_x, to_y, current.vision_radius)

        return cost, hazard_triggered, damage_dice

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

    def reveal_cells(self, cells: list[list[int]], revealed_by_token_id: str | None = None) -> None:
        """Manually reveal specified grid cells."""
        for c in cells:
            if len(c) < 2 or not (0 <= c[0] < self.state.cols and 0 <= c[1] < self.state.rows):
                raise ValueError(f"Reveal coordinates {c} out of grid bounds")
        self.create_event(
            FogOfWarRevealed,
            session_id=self.aggregate_id,
            revealed_cells=cells,
            revealed_by_token_id=revealed_by_token_id,
        )

    def shroud_cells(self, cells: list[list[int]]) -> None:
        """Manually shroud specified grid cells."""
        for c in cells:
            if len(c) < 2 or not (0 <= c[0] < self.state.cols and 0 <= c[1] < self.state.rows):
                raise ValueError(f"Shroud coordinates {c} out of grid bounds")
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
        self._state = BoardState(
            board_id=event.aggregate_id,
            session_id=event.session_id_str or str(event.aggregate_id),
            cols=event.width,
            rows=event.height,
        )

    @handles(TerrainCellModified)
    def _on_terrain_modified(self, event: TerrainCellModified) -> None:
        cells = TerrainDict(self.state.terrain_cells)
        hazard_status = "active" if event.hazard else None
        cell_state = TerrainCellState(
            x=event.x,
            y=event.y,
            elevation=event.elevation,
            terrain_type=event.terrain_type,
            hazard=event.hazard,
            hazard_status=hazard_status,
        )
        cells[(event.x, event.y)] = cell_state
        active_hazards = sorted({c.hazard for c in cells.values() if c.hazard})
        self._state = self.state.model_copy(
            update={"terrain_cells": cells, "active_hazards": active_hazards}
        )

    @handles(TokenHazardTriggered)
    def _on_hazard_triggered(self, event: TokenHazardTriggered) -> None:
        tokens = dict(self.state.tokens)
        tid = str(event.token_id)
        if tid in tokens:
            tokens[tid] = tokens[tid].model_copy(
                update={
                    "active_hazard": event.hazard_type,
                    "hazard_status": "active",
                }
            )
        self._state = self.state.model_copy(update={"tokens": tokens})

    @handles(TokenPlaced)
    def _on_token_placed(self, event: TokenPlaced) -> None:
        tokens = dict(self.state.tokens)
        dest_terrain = self.get_terrain(event.x, event.y)
        active_h = dest_terrain.hazard
        h_status = "active" if active_h else None
        tokens[str(event.token_id)] = PlacedTokenState(
            token_id=str(event.token_id),
            name=event.name,
            token_type=event.token_type,
            x=event.x,
            y=event.y,
            hp=event.hp,
            is_friendly=event.is_friendly,
            active_hazard=active_h,
            hazard_status=h_status,
        )
        self._state = self.state.model_copy(update={"tokens": tokens})

    @handles(TokenMoved)
    def _on_token_moved(self, event: TokenMoved) -> None:
        tokens = dict(self.state.tokens)
        tid_str = str(event.token_id)
        if tid_str in tokens:
            dest_terrain = self.get_terrain(event.to_x, event.to_y)
            active_h = dest_terrain.hazard
            h_status = "active" if active_h else None
            tokens[tid_str] = tokens[tid_str].model_copy(
                update={
                    "x": event.to_x,
                    "y": event.to_y,
                    "active_hazard": active_h,
                    "hazard_status": h_status,
                }
            )
        self._state = self.state.model_copy(update={"tokens": tokens})

    @handles(TokenRemoved)
    def _on_token_removed(self, event: TokenRemoved) -> None:
        tokens = dict(self.state.tokens)
        tokens.pop(str(event.token_id), None)
        self._state = self.state.model_copy(update={"tokens": tokens})

    @handles(FogOfWarRevealed)
    def _on_fog_revealed(self, event: FogOfWarRevealed) -> None:
        existing = {tuple(c) for c in self.state.revealed_cells}
        for cell in event.revealed_cells:
            existing.add(tuple(cell))
        ordered = [list(c) for c in sorted(existing)]
        self._state = self.state.model_copy(update={"revealed_cells": ordered})

    @handles(FogOfWarShrouded)
    def _on_fog_shrouded(self, event: FogOfWarShrouded) -> None:
        to_remove = {tuple(c) for c in event.shrouded_cells}
        remaining = [c for c in self.state.revealed_cells if tuple(c) not in to_remove]
        self._state = self.state.model_copy(update={"revealed_cells": remaining})
