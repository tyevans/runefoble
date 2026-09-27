import type { AoETemplateConfig, BoardToken, GhostPreviewState, TerrainCell } from './board-types.ts';

export const sampleTokens: BoardToken[] = [
  { id: '1', name: 'Valeros', x: 2, y: 3, color: '#2563eb', hp: 38, maxHp: 45, visionRadius: 2 },
  { id: '2', name: 'Kyra (AI)', x: 3, y: 3, isAiControlled: true, color: '#db2777', hp: 28, maxHp: 32, visionRadius: 2 },
  { id: '3', name: 'Goblin Scout', x: 5, y: 1, isHostile: true, color: '#16a34a', hp: 7, maxHp: 12 },
  { id: '4', name: 'Red Dragon Wyrmling', x: 6, y: 5, isHostile: true, color: '#dc2626', hp: 52, maxHp: 75 },
];

export const sampleTerrain: TerrainCell[] = [
  { x: 3, y: 2, terrainType: 'difficult' },
  { x: 4, y: 2, terrainType: 'difficult' },
  { x: 4, y: 3, terrainType: 'difficult' },
  { x: 5, y: 4, terrainType: 'normal', hazard: 'lava' },
];

export const sampleActiveEncounterTokens: BoardToken[] = [
  ...sampleTokens,
  { id: '5', name: 'Ezren', x: 1, y: 4, color: '#9333ea', hp: 22, maxHp: 22, visionRadius: 3 },
];

export const sampleMultiplayerTokens: BoardToken[] = [
  { id: '1', name: 'Valeros', x: 3, y: 4, color: '#2563eb', hp: 42, maxHp: 45, visionRadius: 2 },
  { id: '2', name: 'Kyra (AI)', x: 4, y: 4, isAiControlled: true, color: '#db2777', hp: 12, maxHp: 32, visionRadius: 3 },
  { id: '3', name: 'Merisiel', x: 2, y: 5, color: '#059669', hp: 26, maxHp: 28, visionRadius: 3 },
  { id: '4', name: 'Ezren', x: 4, y: 5, color: '#7c3aed', hp: 18, maxHp: 20, visionRadius: 2 },
  { id: '5', name: 'Skeleton Archer', x: 8, y: 1, isHostile: true, color: '#dc2626', hp: 11, maxHp: 11 },
  { id: '6', name: 'Necromancer', x: 8, y: 8, isHostile: true, color: '#991b1b', hp: 35, maxHp: 40 },
];

export const spokenGhostPreview: GhostPreviewState = {
  tokenId: '1',
  tokenName: 'Valeros',
  fromX: 2,
  fromY: 3,
  toX: 5,
  toY: 3,
  totalDistanceFt: 20,
  baseDistanceFt: 15,
  terrainPenaltyFt: 5,
  movementCost: 4,
  waypoints: [
    { x: 3, y: 3, step: 1, distanceFt: 5, isDifficult: false },
    { x: 4, y: 3, step: 2, distanceFt: 15, isDifficult: true },
    { x: 5, y: 3, step: 3, distanceFt: 20, isDifficult: false },
  ],
  difficultCells: [[4, 3]],
  hazardCells: [],
  timeoutSeconds: 15,
  remainingSeconds: 14,
  speakerName: 'Valeros',
  rawTranscript: 'Valeros charges 3 squares east toward the goblin flank',
};

export const expiringGhostPreview: GhostPreviewState = {
  tokenId: '2',
  tokenName: 'Kyra (AI)',
  fromX: 3,
  fromY: 3,
  toX: 5,
  toY: 4,
  totalDistanceFt: 15,
  waypoints: [
    { x: 4, y: 3, step: 1, distanceFt: 10, isDifficult: true },
    { x: 5, y: 4, step: 2, distanceFt: 15, isDifficult: false, hazard: 'lava' },
  ],
  difficultCells: [[4, 3]],
  hazardCells: [[5, 4]],
  hazardTriggered: 'lava',
  damageDice: '2d10',
  timeoutSeconds: 15,
  remainingSeconds: 4,
  speakerName: 'Kyra',
  rawTranscript: 'Kyra moves toward the molten altar',
};

export const sampleAoETemplates: Record<'cone' | 'sphere', AoETemplateConfig> = {
  cone: {
    shape: 'cone',
    originX: 2.5,
    originY: 3.5,
    directionDeg: 45,
    radiusFt: 15,
    spellName: 'Burning Hands (15-foot Cone)',
    casterTokenId: '1',
  },
  sphere: {
    shape: 'sphere',
    originX: 5.5,
    originY: 2.5,
    directionDeg: 0,
    radiusFt: 20,
    spellName: 'Fireball (20-foot Radius)',
  },
};
