/**
 * Discrete Board Grid Snapper for 3D Miniature Tokens (TASK-0171).
 * Snaps continuous miniature coordinates to discrete board grid centers
 * within 50ms of physics settlement, triggering board state synchronization.
 */

export interface GridSnapTarget {
  tokenId: string;
  rawX: number;
  rawY: number;
  rawZ?: number;
  cols?: number;
  rows?: number;
  walls?: Array<{ x: number; y: number }>;
}

export interface SnapResult {
  tokenId: string;
  fromCoords: [number, number];
  snappedCell: [number, number];
  snappedCenter: [number, number];
  settledZ: number;
  offsetDistance: number;
  settledInMs: number;
  syncedWithin50ms: boolean;
}

export function snapCoordinatesToCell(
  rawX: number, rawY: number, cols = 8, rows = 8, walls?: Array<{ x: number; y: number }>
): [number, number] {
  let cx = Math.max(0, Math.min(cols - 1, Math.round(rawX)));
  let cy = Math.max(0, Math.min(rows - 1, Math.round(rawY)));

  if (walls?.some(w => w.x === cx && w.y === cy)) {
    const candidates = [
      [cx - 1, cy], [cx + 1, cy], [cx, cy - 1], [cx, cy + 1],
      [cx - 1, cy - 1], [cx + 1, cy - 1], [cx - 1, cy + 1], [cx + 1, cy + 1],
    ].filter(([x, y]) => x >= 0 && x < cols && y >= 0 && y < rows && !walls.some(w => w.x === x && w.y === y));

    if (candidates.length > 0) {
      candidates.sort((a, b) => Math.hypot(a[0] - rawX, a[1] - rawY) - Math.hypot(b[0] - rawX, b[1] - rawY));
      cx = candidates[0][0];
      cy = candidates[0][1];
    }
  }
  return [cx, cy];
}

export function snapMiniatureToGrid(target: GridSnapTarget): SnapResult {
  const startTime = performance.now();
  const cols = target.cols ?? 8, rows = target.rows ?? 8;
  const [cx, cy] = snapCoordinatesToCell(target.rawX, target.rawY, cols, rows, target.walls);
  const elapsed = performance.now() - startTime;

  return {
    tokenId: target.tokenId,
    fromCoords: [target.rawX, target.rawY],
    snappedCell: [cx, cy],
    snappedCenter: [cx + 0.5, cy + 0.5],
    settledZ: target.rawZ ?? 0.0,
    offsetDistance: Math.round(Math.hypot(cx - target.rawX, cy - target.rawY) * 100) / 100,
    settledInMs: Math.round(elapsed * 100) / 100,
    syncedWithin50ms: elapsed <= 50.0,
  };
}

export async function scheduleGridSnap(
  target: GridSnapTarget,
  onSync?: (result: SnapResult) => void,
  delayMs = 25
): Promise<SnapResult> {
  const startTime = performance.now();
  const waitMs = Math.min(45, Math.max(0, delayMs));

  return new Promise<SnapResult>((resolve) => {
    setTimeout(() => {
      const res = snapMiniatureToGrid(target);
      const totalElapsed = performance.now() - startTime;
      res.settledInMs = Math.round(totalElapsed * 100) / 100;
      res.syncedWithin50ms = totalElapsed <= 50.0;
      onSync?.(res);
      resolve(res);
    }, waitMs);
  });
}

export function dispatchGridSyncEvent(target: EventTarget, result: SnapResult): boolean {
  return target.dispatchEvent(new CustomEvent('board-grid-snapped', {
    detail: result, bubbles: true, composed: true,
  }));
}
