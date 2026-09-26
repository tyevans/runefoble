import type { BoardToken, GhostPreviewState, TerrainCell } from './board-types.ts';
import { computeGridTrajectory, computeRouteMetrics } from './kinematics.ts';

export interface VectorLineCoords {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  length: number;
  angleDeg: number;
}

export function calculateVectorLineCoordinates(
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
  cellSize: number = 54
): VectorLineCoords {
  // Center coordinates of source and target cells
  const x1 = fromX * cellSize + cellSize / 2;
  const y1 = fromY * cellSize + cellSize / 2;
  const x2 = toX * cellSize + cellSize / 2;
  const y2 = toY * cellSize + cellSize / 2;

  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = Math.sqrt(dx * dx + dy * dy);
  const angleDeg = (Math.atan2(dy, dx) * 180) / Math.PI;

  return { x1, y1, x2, y2, length, angleDeg };
}

export function parseIncomingGhostPreview(
  data: any,
  tokens: BoardToken[],
  terrainCells: TerrainCell[] = []
): GhostPreviewState | null {
  if (!data) return null;

  // Handle server-computed preview
  if (data.preview && typeof data.preview.to_x === 'number') {
    const p = data.preview;
    return {
      tokenId: p.token_id,
      tokenName: p.token_name || p.token_id,
      fromX: p.from_x,
      fromY: p.from_y,
      toX: p.to_x,
      toY: p.to_y,
      totalDistanceFt: p.total_distance_ft,
      baseDistanceFt: p.base_distance_ft,
      terrainPenaltyFt: p.terrain_penalty_ft,
      movementCost: p.movement_cost,
      budgetExceeded: p.budget_exceeded,
      waypoints: (p.waypoints || []).map((w: any) => ({
        x: w.x,
        y: w.y,
        step: w.step,
        distanceFt: w.distance_ft,
        isDifficult: w.is_difficult,
        hazard: w.hazard,
      })),
      difficultCells: p.difficult_cells || [],
      hazardCells: p.hazard_cells || [],
      hazardTriggered: p.hazard_triggered,
      damageDice: p.damage_dice,
      timeoutSeconds: data.timeout_seconds || 15,
      remainingSeconds: data.timeout_seconds || 15,
      speakerName: data.speaker_name,
      rawTranscript: data.raw_transcript,
    };
  }

  // Handle direct spoken intent or client-side intent message
  const tokenId = data.token_id || data.tokenId;
  const speakerName = data.speaker_name || data.speakerName;
  const token = tokens.find(
    (t) => t.id === tokenId || (speakerName && t.name.toLowerCase() === speakerName.toLowerCase())
  );

  if (!token && !tokenId) return null;

  const actualTokenId = token ? token.id : tokenId;
  const fromX = typeof data.from_x === 'number' ? data.from_x : (token?.x ?? 0);
  const fromY = typeof data.from_y === 'number' ? data.from_y : (token?.y ?? 0);
  const toX = typeof data.to_x === 'number' ? data.to_x : fromX;
  const toY = typeof data.to_y === 'number' ? data.to_y : fromY;

  const path = computeGridTrajectory(fromX, fromY, toX, toY);
  const metrics = computeRouteMetrics(path, terrainCells);

  return {
    tokenId: actualTokenId,
    tokenName: token?.name || actualTokenId,
    fromX,
    fromY,
    toX,
    toY,
    totalDistanceFt: metrics.totalDistanceFt,
    baseDistanceFt: metrics.baseDistanceFt,
    terrainPenaltyFt: metrics.terrainPenaltyFt,
    movementCost: metrics.movementCost,
    waypoints: metrics.waypoints,
    difficultCells: metrics.difficultCells,
    hazardCells: metrics.hazardCells,
    timeoutSeconds: data.timeout_seconds || 15,
    remainingSeconds: data.timeout_seconds || 15,
    speakerName,
    rawTranscript: data.raw_transcript || data.transcript,
    color: token?.color,
  };
}

export class GhostPreviewEngine {
  private activePreview: GhostPreviewState | null = null;
  private timerId: number | null = null;
  private onUpdate: ((preview: GhostPreviewState | null) => void) | null = null;
  private onTimeout: (() => void) | null = null;

  constructor(
    onUpdate?: (preview: GhostPreviewState | null) => void,
    onTimeout?: () => void
  ) {
    this.onUpdate = onUpdate ?? null;
    this.onTimeout = onTimeout ?? null;
  }

  public get current(): GhostPreviewState | null {
    return this.activePreview;
  }

  public stage(preview: GhostPreviewState): void {
    this.clearTimer();
    this.activePreview = { ...preview };
    if (this.onUpdate) {
      this.onUpdate(this.activePreview);
    }
    this.startCountdown();
  }

  public cancel(): void {
    this.clearTimer();
    this.activePreview = null;
    if (this.onUpdate) {
      this.onUpdate(null);
    }
  }

  public confirm(): GhostPreviewState | null {
    const committed = this.activePreview;
    this.clearTimer();
    this.activePreview = null;
    if (this.onUpdate) {
      this.onUpdate(null);
    }
    return committed;
  }

  private startCountdown(): void {
    if (!this.activePreview) return;
    this.timerId = window.setInterval(() => {
      if (!this.activePreview) {
        this.clearTimer();
        return;
      }
      this.activePreview.remainingSeconds -= 1;
      if (this.activePreview.remainingSeconds <= 0) {
        this.clearTimer();
        this.activePreview = null;
        if (this.onTimeout) this.onTimeout();
        if (this.onUpdate) this.onUpdate(null);
      } else if (this.onUpdate) {
        this.onUpdate({ ...this.activePreview });
      }
    }, 1000);
  }

  private clearTimer(): void {
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }

  public dispose(): void {
    this.clearTimer();
    this.activePreview = null;
    this.onUpdate = null;
    this.onTimeout = null;
  }
}
