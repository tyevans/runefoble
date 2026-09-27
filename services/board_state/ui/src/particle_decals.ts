/**
 * Ephemeral combat grid decal rendering, opacity decay curves, and lifecycle management.
 */

import type { DecalType, EphemeralDecal } from './particle_types.ts';

const DECAL_COLORS: Record<DecalType, [number, number, number]> = {
  scorched_earth: [180, 70, 20],
  frost: [80, 200, 240],
  lightning_scorch: [140, 100, 240],
  abjuration_glyph: [220, 180, 50],
  portal_residue: [150, 50, 220],
};

export function calculateDecalOpacity(
  roundsRemaining: number,
  durationRounds: number,
  minOpacity = 0.15,
  maxOpacity = 0.85
): number {
  if (durationRounds <= 0) return minOpacity;
  const ratio = Math.max(0, roundsRemaining / durationRounds);
  return Math.max(minOpacity, ratio * maxOpacity);
}

export function createEphemeralDecal(
  x: number,
  y: number,
  decalType: DecalType,
  durationRounds = 2
): EphemeralDecal {
  return {
    id: `decal-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
    x,
    y,
    decalType,
    durationRounds,
    roundsRemaining: durationRounds,
    opacity: 0.85,
    createdAt: Date.now(),
  };
}

export function renderDecals2D(
  ctx: CanvasRenderingContext2D,
  decals: EphemeralDecal[],
  cellSizePx: number
): void {
  for (const d of decals) {
    const cx = d.x * cellSizePx + cellSizePx / 2;
    const cy = d.y * cellSizePx + cellSizePx / 2;
    const radius = cellSizePx * 0.42;
    const [r, g, b] = DECAL_COLORS[d.decalType] ?? [200, 100, 50];

    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${d.opacity * 0.35})`;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${d.opacity * 0.7})`;
    ctx.stroke();
    ctx.restore();
  }
}

export class DecalManager {
  private decals: EphemeralDecal[] = [];

  public add(x: number, y: number, decalType: DecalType, durationRounds = 2): EphemeralDecal {
    const decal = createEphemeralDecal(x, y, decalType, durationRounds);
    this.decals.push(decal);
    return decal;
  }

  public decay(rounds = 1): EphemeralDecal[] {
    for (const d of this.decals) {
      d.roundsRemaining -= rounds;
      d.opacity = calculateDecalOpacity(d.roundsRemaining, d.durationRounds);
    }
    this.decals = this.decals.filter((d) => d.roundsRemaining > 0);
    return this.decals;
  }

  public getDecals(): EphemeralDecal[] {
    return this.decals;
  }

  public get count(): number {
    return this.decals.length;
  }

  public clear(): void {
    this.decals = [];
  }

  public render2D(ctx: CanvasRenderingContext2D, cellSizePx: number): void {
    renderDecals2D(ctx, this.decals, cellSizePx);
  }
}
