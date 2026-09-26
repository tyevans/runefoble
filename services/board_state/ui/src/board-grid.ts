import { html } from 'lit';
import type {
  BoardToken,
  DragKinematicsState,
  GhostPreviewState,
  TerrainCell,
} from './board-types.ts';
import { calculateVectorLineCoordinates } from './ghost_preview.ts';
import { isCellVisible } from './kinematics.ts';
import {
  renderBoardCell,
  renderDistanceRuler,
  renderVectorOverlay,
} from './board-templates.ts';

export interface BoardGridRenderOptions {
  cols: number;
  rows: number;
  tokens: BoardToken[];
  terrainCells: TerrainCell[];
  activeTurnTokenId: string | null;
  selectedTokenId: string | null;
  dragState: DragKinematicsState | null;
  localGhost: GhostPreviewState | null;
  fogOfWar: boolean;
  isCellRevealed?: (x: number, y: number) => boolean;
  onCellClick: (x: number, y: number) => void;
  onTokenPointerDown: (e: PointerEvent, token: BoardToken) => void;
  onPointerMove: (e: PointerEvent) => void;
  onPointerUp: (e: PointerEvent) => void;
  onGhostConfirm: () => void;
}

export function renderBoardGrid(options: BoardGridRenderOptions) {
  const {
    cols,
    rows,
    tokens,
    terrainCells,
    activeTurnTokenId,
    selectedTokenId,
    dragState,
    localGhost,
    fogOfWar,
    isCellRevealed: checkRevealed,
    onCellClick,
    onTokenPointerDown,
    onPointerMove,
    onPointerUp,
    onGhostConfirm,
  } = options;

  const gridStyle = `grid-template-columns: repeat(${cols}, 54px); grid-template-rows: repeat(${rows}, 54px);`;

  let ghostVector: ReturnType<typeof calculateVectorLineCoordinates> | null = null;
  if (localGhost && (localGhost.fromX !== localGhost.toX || localGhost.fromY !== localGhost.toY)) {
    ghostVector = calculateVectorLineCoordinates(
      localGhost.fromX,
      localGhost.fromY,
      localGhost.toX,
      localGhost.toY,
      56
    );
  }

  const activeWaypoints = dragState?.isDragging
    ? dragState.waypoints
    : (localGhost?.waypoints || []);

  const waypointSet = new Set(activeWaypoints.map((w) => `${w.x},${w.y}`));

  return html`
    <div class="grid-wrapper">
      <div
        class="grid"
        style="${gridStyle}"
        @pointermove="${onPointerMove}"
        @pointerup="${onPointerUp}"
      >
        ${renderVectorOverlay(ghostVector)}

        ${Array.from({ length: rows * cols }).map((_, index) => {
          const x = index % cols;
          const y = Math.floor(index / cols);
          const isRevealed = checkRevealed ? checkRevealed(x, y) : isCellVisible(x, y, fogOfWar, tokens);
          const token = tokens.find((t) => t.x === x && t.y === y);
          const isActiveTurn = Boolean(
            token && (token.isActiveTurn || token.id === activeTurnTokenId)
          );
          const isGhostCell = Boolean(localGhost && localGhost.toX === x && localGhost.toY === y);
          const ghostToken = localGhost ? tokens.find((t) => t.id === localGhost.tokenId) : null;

          return renderBoardCell({
            x,
            y,
            isRevealed,
            terrain: terrainCells.find((c) => c.x === x && c.y === y),
            isWaypoint: waypointSet.has(`${x},${y}`),
            token,
            isActiveTurn,
            isGhostCell,
            ghostToken,
            ghostName: localGhost?.tokenName,
            selectedTokenId,
            draggingTokenId: dragState?.tokenId ?? null,
            onCellClick: () => onCellClick(x, y),
            onTokenPointerDown: (e, t) => onTokenPointerDown(e, t),
            onGhostConfirm,
          });
        })}
      </div>

      ${renderDistanceRuler(dragState)}
    </div>
  `;
}
