import type { BoardToken, DragKinematicsState, TerrainCell, Waypoint } from './board-types.ts';

export function computeGridTrajectory(
  fromX: number,
  fromY: number,
  toX: number,
  toY: number
): [number, number][] {
  const dx = toX - fromX;
  const dy = toY - fromY;
  const steps = Math.max(Math.abs(dx), Math.abs(dy));
  if (steps === 0) return [];

  const path: [number, number][] = [];
  for (let step = 1; step <= steps; step++) {
    const cx = Math.round(fromX + step * (dx / steps));
    const cy = Math.round(fromY + step * (dy / steps));
    path.push([cx, cy]);
  }
  return path;
}

export function computeRouteMetrics(
  path: [number, number][],
  terrainCells: TerrainCell[]
): {
  totalDistanceFt: number;
  baseDistanceFt: number;
  terrainPenaltyFt: number;
  movementCost: number;
  waypoints: Waypoint[];
  difficultCells: [number, number][];
  hazardCells: [number, number][];
} {
  const terrainMap = new Map<string, TerrainCell>();
  for (const cell of terrainCells) {
    terrainMap.set(`${cell.x},${cell.y}`, cell);
  }

  const waypoints: Waypoint[] = [];
  const difficultCells: [number, number][] = [];
  const hazardCells: [number, number][] = [];
  let cumulativeDistanceFt = 0;
  let terrainPenaltyFt = 0;
  let movementCost = 0;

  path.forEach(([cx, cy], index) => {
    const cell = terrainMap.get(`${cx},${cy}`);
    const isDifficult = cell?.terrainType === 'difficult';
    const hazard = cell?.hazard ?? null;

    // Normal = 5ft, difficult = 10ft (+5ft penalty)
    const stepFt = isDifficult ? 10 : 5;
    cumulativeDistanceFt += stepFt;
    movementCost += isDifficult ? 2 : 1;

    if (isDifficult) {
      difficultCells.push([cx, cy]);
      terrainPenaltyFt += 5;
    }
    if (hazard) {
      hazardCells.push([cx, cy]);
    }

    waypoints.push({
      x: cx,
      y: cy,
      step: index + 1,
      distanceFt: cumulativeDistanceFt,
      isDifficult,
      hazard,
    });
  });

  return {
    totalDistanceFt: cumulativeDistanceFt,
    baseDistanceFt: path.length * 5,
    terrainPenaltyFt,
    movementCost,
    waypoints,
    difficultCells,
    hazardCells,
  };
}

export function snapToGrid(
  offsetX: number,
  offsetY: number,
  cellSize: number = 54,
  cols: number = 8,
  rows: number = 8
): { cellX: number; cellY: number } {
  const rawX = Math.floor(offsetX / cellSize);
  const rawY = Math.floor(offsetY / cellSize);
  const cellX = Math.max(0, Math.min(cols - 1, rawX));
  const cellY = Math.max(0, Math.min(rows - 1, rawY));
  return { cellX, cellY };
}

export function springInterpolate(
  current: number,
  target: number,
  factor: number = 0.3
): number {
  return current + (target - current) * factor;
}

export function isCellVisible(
  cellX: number,
  cellY: number,
  fogOfWar: boolean,
  tokens: BoardToken[]
): boolean {
  if (!fogOfWar) return true;
  const friendlyTokens = tokens.filter((t) => !t.isHostile);
  if (friendlyTokens.length === 0) return true;
  return friendlyTokens.some((token) => {
    const radius = token.visionRadius ?? 2;
    const dx = Math.abs(token.x - cellX);
    const dy = Math.abs(token.y - cellY);
    return Math.max(dx, dy) <= radius;
  });
}

export function initDragState(token: BoardToken): DragKinematicsState {
  return {
    tokenId: token.id,
    startX: token.x,
    startY: token.y,
    currentX: token.x,
    currentY: token.y,
    targetCellX: token.x,
    targetCellY: token.y,
    isDragging: true,
    totalDistanceFt: 0,
    waypoints: [],
    difficultCells: [],
    hazardCells: [],
  };
}

export function computeDragUpdate(
  dragState: DragKinematicsState,
  cellX: number,
  cellY: number,
  terrainCells: TerrainCell[]
): DragKinematicsState {
  if (cellX === dragState.targetCellX && cellY === dragState.targetCellY) {
    return dragState;
  }
  const path = computeGridTrajectory(
    dragState.startX,
    dragState.startY,
    cellX,
    cellY
  );
  const metrics = computeRouteMetrics(path, terrainCells);
  return {
    ...dragState,
    targetCellX: cellX,
    targetCellY: cellY,
    totalDistanceFt: metrics.totalDistanceFt,
    waypoints: metrics.waypoints,
    difficultCells: metrics.difficultCells,
    hazardCells: metrics.hazardCells,
  };
}
