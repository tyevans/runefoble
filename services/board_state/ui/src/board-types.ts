export interface BoardToken {
  id: string;
  name: string;
  x: number;
  y: number;
  avatarUrl?: string;
  isAiControlled?: boolean;
  color?: string;
  hp?: number;
  maxHp?: number;
  visionRadius?: number;
  isHostile?: boolean;
  isActiveTurn?: boolean;
  movementBudget?: number;
}

export type TerrainType = 'normal' | 'difficult';

export interface TerrainCell {
  x: number;
  y: number;
  elevation?: number;
  terrainType: TerrainType;
  hazard?: string | null;
}

export interface Waypoint {
  x: number;
  y: number;
  step: number;
  distanceFt: number;
  isDifficult?: boolean;
  hazard?: string | null;
}

export interface GhostPreviewState {
  tokenId: string;
  tokenName?: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  totalDistanceFt: number;
  baseDistanceFt?: number;
  terrainPenaltyFt?: number;
  movementCost?: number;
  budgetExceeded?: boolean;
  waypoints: Waypoint[];
  difficultCells: [number, number][];
  hazardCells: [number, number][];
  hazardTriggered?: string | null;
  damageDice?: string | null;
  timeoutSeconds: number;
  remainingSeconds: number;
  speakerName?: string;
  rawTranscript?: string;
  color?: string;
}

export interface DragKinematicsState {
  tokenId: string;
  startX: number;
  startY: number;
  currentX: number; // grid relative coordinate
  currentY: number; // grid relative coordinate
  targetCellX: number;
  targetCellY: number;
  isDragging: boolean;
  totalDistanceFt: number;
  waypoints: Waypoint[];
  difficultCells: [number, number][];
  hazardCells: [number, number][];
}
