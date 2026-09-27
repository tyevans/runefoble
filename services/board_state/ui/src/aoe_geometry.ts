import type { AoETemplateConfig, BoardToken } from './aoe_types.ts';

export const CONE_SPREAD_DEG = 53.13; // Standard 5e cone spread angle

export function snapAngle(deg: number, increment = 15): number {
  if (increment <= 0) return ((deg % 360) + 360) % 360;
  const snapped = Math.round(deg / increment) * increment;
  return ((snapped % 360) + 360) % 360;
}

export function normalizeAngleDiff(angle1: number, angle2: number): number {
  return Math.abs((((angle1 - angle2 + 180) % 360) + 360) % 360 - 180);
}

export function isPointInAoEGeometry(
  targetFtX: number,
  targetFtY: number,
  config: AoETemplateConfig
): boolean {
  const { shape, originX, originY, directionDeg, radiusFt = 15, lengthFt = 30, widthFt = 5 } = config;
  const origFtX = originX * 5.0;
  const origFtY = originY * 5.0;
  const dx = targetFtX - origFtX;
  const dy = targetFtY - origFtY;
  const dist = Math.hypot(dx, dy);

  if (shape === 'cone') {
    if (dist <= 0.001) return true;
    if (dist > radiusFt + 0.05) return false;
    const ptAngle = ((Math.atan2(dy, dx) * 180) / Math.PI + 360) % 360;
    const angleDiff = normalizeAngleDiff(ptAngle, directionDeg);
    return angleDiff <= CONE_SPREAD_DEG / 2 + 0.05;
  }

  if (shape === 'sphere') {
    return dist <= (radiusFt || 20) + 0.05;
  }

  if (shape === 'line') {
    const rad = (directionDeg * Math.PI) / 180;
    const ux = Math.cos(rad);
    const uy = Math.sin(rad);
    const vx = -Math.sin(rad);
    const vy = Math.cos(rad);

    const projAlong = dx * ux + dy * uy;
    const projPerp = Math.abs(dx * vx + dy * vy);

    return projAlong >= -0.05 && projAlong <= (lengthFt || 30) + 0.05 && projPerp <= widthFt / 2 + 0.05;
  }

  if (shape === 'cube') {
    const rad = (directionDeg * Math.PI) / 180;
    const size = radiusFt || lengthFt || 20;
    const ux = Math.cos(rad);
    const uy = Math.sin(rad);
    const vx = -Math.sin(rad);
    const vy = Math.cos(rad);

    const projX = Math.abs(dx * ux + dy * uy);
    const projY = Math.abs(dx * vx + dy * vy);
    return projX <= size / 2 + 0.05 && projY <= size / 2 + 0.05;
  }

  return false;
}

export function isTokenInAoE(token: BoardToken, config: AoETemplateConfig): boolean {
  const targetFtX = (token.x + 0.5) * 5.0;
  const targetFtY = (token.y + 0.5) * 5.0;
  return isPointInAoEGeometry(targetFtX, targetFtY, config);
}

export function computeAffectedTokens(tokens: BoardToken[], config: AoETemplateConfig): string[] {
  return tokens.filter((t) => isTokenInAoE(t, config)).map((t) => t.id);
}

export function computeAffectedCells(
  cols: number,
  rows: number,
  config: AoETemplateConfig
): [number, number][] {
  const affected: [number, number][] = [];
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const cellFtX = (x + 0.5) * 5.0;
      const cellFtY = (y + 0.5) * 5.0;
      if (isPointInAoEGeometry(cellFtX, cellFtY, config)) {
        affected.push([x, y]);
      }
    }
  }
  return affected;
}
