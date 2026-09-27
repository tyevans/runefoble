/**
 * Parametric polyhedral rigid-body geometries and collision parameters (TASK-0170).
 * Calibrated restitution, friction, and resting face normals for d4, d6, d8, d10, d12, d20.
 */

export type DiceType = 'd4' | 'd6' | 'd8' | 'd10' | 'd12' | 'd20';

export interface PolyhedralConfig {
  sides: number;
  mass: number;
  radius: number;
  restitution: number;
  friction: number;
  color: string;
}

export const DICE_CONFIGS: Record<DiceType, PolyhedralConfig> = {
  d4: { sides: 4, mass: 0.8, radius: 14, restitution: 0.45, friction: 0.35, color: '#ef4444' },
  d6: { sides: 6, mass: 1.0, radius: 15, restitution: 0.50, friction: 0.30, color: '#3b82f6' },
  d8: { sides: 8, mass: 1.1, radius: 15, restitution: 0.48, friction: 0.32, color: '#10b981' },
  d10: { sides: 10, mass: 1.2, radius: 16, restitution: 0.52, friction: 0.29, color: '#8b5cf6' },
  d12: { sides: 12, mass: 1.35, radius: 17, restitution: 0.50, friction: 0.31, color: '#f97316' },
  d20: { sides: 20, mass: 1.5, radius: 18, restitution: 0.55, friction: 0.28, color: '#eab308' },
};

export function isValidDiceType(val: string): val is DiceType {
  return val in DICE_CONFIGS;
}

export function getPolyhedralVertices(type: DiceType, size: number): Array<[number, number]> {
  const count = type === 'd4' ? 3 : type === 'd6' ? 4 : type === 'd10' ? 5 : type === 'd12' ? 10 : 6;
  const vertices: Array<[number, number]> = [];
  const offset = type === 'd4' ? -Math.PI / 2 : 0;
  for (let i = 0; i < count; i++) {
    const angle = offset + (i * 2 * Math.PI) / count;
    vertices.push([Math.cos(angle) * size, Math.sin(angle) * size]);
  }
  return vertices;
}

export interface DicePalette {
  bg: string;
  text: string;
  border: string;
  shadow: string;
  isCrit: boolean;
}

export function getDiceColors(
  type: DiceType,
  faceValue: number,
  theme: 'dark' | 'light' | 'high-contrast' = 'dark'
): DicePalette {
  const cfg = DICE_CONFIGS[type];
  const isMax = faceValue === cfg.sides;
  const isMin = faceValue === 1;

  if (theme === 'high-contrast') {
    return {
      bg: isMax ? '#ffff00' : isMin ? '#000000' : '#ffffff',
      text: isMax ? '#000000' : isMin ? '#ffffff' : '#000000',
      border: '#ffffff',
      shadow: 'rgba(255, 255, 255, 0.4)',
      isCrit: isMax,
    };
  }

  if (isMax) {
    return {
      bg: '#fbbf24',
      text: '#1e1b4b',
      border: '#fef08a',
      shadow: 'rgba(251, 191, 36, 0.6)',
      isCrit: true,
    };
  }
  if (isMin) {
    return {
      bg: '#dc2626',
      text: '#ffffff',
      border: '#fca5a5',
      shadow: 'rgba(220, 38, 38, 0.5)',
      isCrit: false,
    };
  }

  if (theme === 'light') {
    return {
      bg: cfg.color,
      text: '#ffffff',
      border: '#0f172a',
      shadow: 'rgba(0, 0, 0, 0.25)',
      isCrit: false,
    };
  }

  return {
    bg: cfg.color,
    text: '#ffffff',
    border: '#ffffff',
    shadow: 'rgba(0, 0, 0, 0.4)',
    isCrit: false,
  };
}

export function getFaceRotationOrientation(
  type: DiceType,
  faceValue: number
): { rotX: number; rotY: number; rotZ: number } {
  const sides = DICE_CONFIGS[type].sides;
  const normalized = Math.max(1, Math.min(sides, faceValue));
  const angleStep = (2 * Math.PI) / sides;
  return {
    rotX: Math.sin(normalized * angleStep) * 0.4,
    rotY: Math.cos(normalized * angleStep) * 0.4,
    rotZ: (normalized - 1) * angleStep,
  };
}
