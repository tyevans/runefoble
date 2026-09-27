/**
 * Projectile physics, parabolic arc interpolation, and collision tracking for spell VFX.
 */

import { getArchetypeColor } from './particle_archetypes.ts';
import type {
  ActiveProjectile,
  Particle,
  SpellArchetype,
  SpellVFXParams,
} from './particle_types.ts';

export function calculateParabolicTrajectory(
  startX: number,
  startY: number,
  targetX: number,
  targetY: number,
  progress: number,
  arcHeight = 0
): { x: number; y: number } {
  const clampedProgress = Math.min(1.0, Math.max(0, progress));
  const linearX = startX + (targetX - startX) * clampedProgress;
  const linearY = startY + (targetY - startY) * clampedProgress;
  const parabolicOffset = arcHeight * 4 * clampedProgress * (1 - clampedProgress);
  return { x: linearX, y: linearY - parabolicOffset };
}

export function hasProjectileCollided(projectile: ActiveProjectile): boolean {
  return projectile.progress >= 1.0;
}

export function createProjectileTrailParticle(p: ActiveProjectile): Particle {
  return {
    x: p.currentX + (Math.random() - 0.5) * 4,
    y: p.currentY + (Math.random() - 0.5) * 4,
    vx: (Math.random() - 0.5) * 0.8,
    vy: (Math.random() - 0.5) * 0.8,
    size: 4 + Math.random() * 4,
    initialSize: 6,
    color: [p.color[0], p.color[1], p.color[2], 0.8],
    life: 1.0,
    maxLife: 0.25,
    age: 0,
    type: 0,
    rotation: 0,
    rotationSpeed: 0,
  };
}

export function createActiveProjectile(
  params: SpellVFXParams,
  startPx: { x: number; y: number },
  targetPx: { x: number; y: number },
  cellSizePx: number,
  onImpact: () => void
): ActiveProjectile {
  const archetype: SpellArchetype = params.spellArchetype ?? 'evocation';
  const dist = Math.hypot(targetPx.x - startPx.x, targetPx.y - startPx.y);
  const durationMs = Math.min(320, Math.max(160, dist * 0.9));

  return {
    id: `proj-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
    spellName: params.spellName,
    spellArchetype: archetype,
    currentX: startPx.x,
    currentY: startPx.y,
    targetX: targetPx.x,
    targetY: targetPx.y,
    toGridX: params.toX,
    toGridY: params.toY,
    radiusPx: ((params.radiusFt ?? 20) / 5) * cellSizePx,
    color: getArchetypeColor(archetype, params.damageType),
    progress: 0,
    durationMs,
    elapsedMs: 0,
    startX: startPx.x,
    startY: startPx.y,
    onImpact,
    onFinish: params.onFinish,
  };
}

export class ProjectileManager {
  private projectiles: ActiveProjectile[] = [];

  public add(projectile: ActiveProjectile): void {
    this.projectiles.push(projectile);
  }

  public get count(): number {
    return this.projectiles.length;
  }

  public get all(): ActiveProjectile[] {
    return this.projectiles;
  }

  public clear(): void {
    this.projectiles = [];
  }

  public update(deltaMs: number, onSpawnTrail: (p: Particle) => void): void {
    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      const p = this.projectiles[i];
      p.elapsedMs += deltaMs;
      p.progress = Math.min(1.0, p.elapsedMs / p.durationMs);

      const pos = calculateParabolicTrajectory(p.startX, p.startY, p.targetX, p.targetY, p.progress);
      p.currentX = pos.x;
      p.currentY = pos.y;

      onSpawnTrail(createProjectileTrailParticle(p));

      if (hasProjectileCollided(p)) {
        p.onImpact?.();
        p.onFinish?.();
        this.projectiles.splice(i, 1);
      }
    }
  }
}
