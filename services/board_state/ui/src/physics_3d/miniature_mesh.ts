/**
 * 3D Miniature Token Mesh Generator and Renderer.
 * Extrudes 2D circular tokens into stylized 3D miniature figurines with
 * weighted bevelled bases, character portrait discs, elevation offsets, and condition rings.
 */

export type MiniatureCondition = 'none' | 'stunned' | 'fire' | 'blessed' | 'poisoned' | 'targeted';

export interface Miniature3DToken {
  id: string;
  name: string;
  x: number;
  y: number;
  z?: number;
  color?: string;
  hp?: number;
  maxHp?: number;
  isHostile?: boolean;
  isAiControlled?: boolean;
  isActiveTurn?: boolean;
  condition?: MiniatureCondition;
  tiltAngleX?: number;
  tiltAngleY?: number;
}

export interface Camera3D {
  rotX: number;
  rotY: number;
  zoom: number;
}

export function project3D(
  gx: number, gy: number, gz: number,
  cellSizePx: number, cam: Camera3D, originX: number, originY: number
): { px: number; py: number; depth: number } {
  const radX = (cam.rotX * Math.PI) / 180, radY = (cam.rotY * Math.PI) / 180;
  const worldX = (gx - originX) * cellSizePx, worldY = (gy - originY) * cellSizePx;
  const worldZ = gz * (cellSizePx * 0.35);
  const rotY_X = worldX * Math.cos(radY) - worldY * Math.sin(radY);
  const rotY_Y = worldX * Math.sin(radY) + worldY * Math.cos(radY);
  const projX = rotY_X * cam.zoom;
  const projY = (rotY_Y * Math.sin(radX) - worldZ * Math.cos(radX)) * cam.zoom;
  return { px: projX, py: projY, depth: rotY_Y * Math.cos(radX) + worldZ * Math.sin(radX) };
}

export function getConditionColor(cond?: MiniatureCondition): string | null {
  const colors: Record<string, string> = {
    stunned: '#eab308', fire: '#ef4444', blessed: '#06b6d4', poisoned: '#22c55e', targeted: '#f97316',
  };
  return cond ? colors[cond] ?? null : null;
}

export function renderMiniatureBase(
  ctx: CanvasRenderingContext2D,
  centerPx: { x: number; y: number },
  token: Miniature3DToken,
  radiusPx = 20,
  baseHeightPx = 8
): void {
  const { x, y } = centerPx;
  const tiltX = token.tiltAngleX ?? 0, tiltY = token.tiltAngleY ?? 0;
  const baseColor = token.color || (token.isHostile ? '#dc2626' : '#2563eb');
  const condColor = getConditionColor(token.condition);

  ctx.save();
  ctx.translate(x, y);
  if (tiltX !== 0 || tiltY !== 0) ctx.transform(1, tiltY * 0.3, tiltX * 0.3, 1, 0, 0);

  // Drop shadow
  ctx.beginPath();
  ctx.ellipse(2, 4 + baseHeightPx, radiusPx * 1.05, radiusPx * 0.55, 0, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
  ctx.fill();

  // 3D Extruded Cylinder Body
  const bevelGrad = ctx.createLinearGradient(-radiusPx, 0, radiusPx, baseHeightPx);
  bevelGrad.addColorStop(0, '#1e293b');
  bevelGrad.addColorStop(0.5, '#475569');
  bevelGrad.addColorStop(1, '#0f172a');
  ctx.beginPath();
  ctx.ellipse(0, baseHeightPx, radiusPx, radiusPx * 0.5, 0, 0, Math.PI);
  ctx.lineTo(-radiusPx, 0);
  ctx.ellipse(0, 0, radiusPx, radiusPx * 0.5, 0, Math.PI, 0, true);
  ctx.closePath();
  ctx.fillStyle = bevelGrad;
  ctx.fill();
  ctx.strokeStyle = '#0f172a';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // Top Base Surface
  ctx.beginPath();
  ctx.ellipse(0, 0, radiusPx, radiusPx * 0.5, 0, 0, Math.PI * 2);
  ctx.fillStyle = baseColor;
  ctx.fill();
  ctx.stroke();

  // Snap-on Condition Ring
  if (condColor) {
    ctx.beginPath();
    ctx.ellipse(0, -1, radiusPx * 1.12, radiusPx * 0.56, 0, 0, Math.PI * 2);
    ctx.strokeStyle = condColor;
    ctx.lineWidth = 3.5;
    ctx.stroke();
  }

  // Active Turn Halo
  if (token.isActiveTurn) {
    ctx.beginPath();
    ctx.ellipse(0, -2, radiusPx * 1.25, radiusPx * 0.62, 0, 0, Math.PI * 2);
    ctx.strokeStyle = '#facc15';
    ctx.lineWidth = 2.5;
    ctx.stroke();
  }

  // Miniature Portrait Medallion & Label
  ctx.beginPath();
  ctx.ellipse(0, -baseHeightPx * 0.5, radiusPx * 0.72, radiusPx * 0.36, 0, 0, Math.PI * 2);
  ctx.fillStyle = '#f8fafc';
  ctx.fill();
  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 11px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(token.name.slice(0, 2).toUpperCase(), 0, -baseHeightPx * 0.5);

  // Floating HP pip
  if (token.hp !== undefined && token.maxHp !== undefined) {
    const hpRatio = Math.max(0, Math.min(1, token.hp / token.maxHp));
    const barW = radiusPx * 1.4, barY = -radiusPx * 0.7 - baseHeightPx;
    ctx.fillStyle = 'rgba(15, 23, 42, 0.8)';
    ctx.fillRect(-barW / 2, barY, barW, 3);
    ctx.fillStyle = hpRatio > 0.5 ? '#22c55e' : hpRatio > 0.2 ? '#f59e0b' : '#ef4444';
    ctx.fillRect(-barW / 2, barY, barW * hpRatio, 3);
  }
  ctx.restore();
}

export function renderElevationCliff(
  ctx: CanvasRenderingContext2D,
  centerPx: { x: number; y: number },
  elevation: number,
  cellSizePx = 54,
  zoom = 1.0
): void {
  if (elevation <= 0) return;
  const cliffHeight = elevation * 14 * zoom;
  const hw = cellSizePx * 0.48 * zoom, hh = cellSizePx * 0.26 * zoom;
  const { x, y } = centerPx;

  ctx.save();
  ctx.beginPath();
  ctx.moveTo(x - hw, y);
  ctx.lineTo(x, y + hh);
  ctx.lineTo(x + hw, y);
  ctx.lineTo(x + hw, y + cliffHeight);
  ctx.lineTo(x, y + hh + cliffHeight);
  ctx.lineTo(x - hw, y + cliffHeight);
  ctx.closePath();
  ctx.fillStyle = '#1e293b';
  ctx.fill();
  ctx.strokeStyle = '#0f172a';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(x, y - hh);
  ctx.lineTo(x + hw, y);
  ctx.lineTo(x, y + hh);
  ctx.lineTo(x - hw, y);
  ctx.closePath();
  ctx.fillStyle = '#475569';
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}
