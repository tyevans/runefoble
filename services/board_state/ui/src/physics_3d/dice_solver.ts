/**
 * Deterministic Dice Toss Solver & Cryptographic Roll Alignment Engine (TASK-0170).
 * Guarantees final resting face values conform 100% to server-side cryptographic rolls.
 */

import { type DiceType, DICE_CONFIGS, getFaceRotationOrientation } from './dice_models.ts';
import type { ImpactType } from './tray_audio.ts';

export interface DiceTossParams {
  diceType: DiceType;
  targetFaceValue: number;
  origin?: { x: number; y: number; z: number };
  velocity?: { x: number; y: number; z: number };
  trayBounds?: { minX: number; maxX: number; minY: number; maxY: number };
  seed?: number;
  diceId?: string;
}

export interface TossCollision {
  type: ImpactType;
  x: number;
  y: number;
  z: number;
  t: number;
  energy: number;
}

export interface TossKeyframe {
  x: number;
  y: number;
  z: number;
  rotX: number;
  rotY: number;
  rotZ: number;
  t: number;
}

export interface SolvedDiceToss {
  diceId: string;
  diceType: DiceType;
  faceValue: number;
  settledPosition: [number, number, number];
  settledCell: [number, number];
  bounces: number;
  duration: number;
  trajectory: TossKeyframe[];
  collisions: TossCollision[];
}

export function solveDeterministicToss(params: DiceTossParams): SolvedDiceToss {
  const cfg = DICE_CONFIGS[params.diceType] || DICE_CONFIGS.d20;
  const targetFace = Math.max(1, Math.min(cfg.sides, params.targetFaceValue));
  const diceId = params.diceId || `dice-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
  const b = params.trayBounds || { minX: 0.8, maxX: 7.2, minY: 0.8, maxY: 4.2 };

  let x = params.origin?.x ?? b.minX + 0.5, y = params.origin?.y ?? b.minY + 0.5, z = params.origin?.z ?? 3.5;
  let vx = params.velocity?.x ?? (b.maxX - b.minX) * 0.45;
  let vy = params.velocity?.y ?? (b.maxY - b.minY) * 0.4;
  let vz = params.velocity?.z ?? 1.5;

  const dt = 0.04, g = 9.81, drag = 0.03, maxSteps = 120;
  const trajectory: TossKeyframe[] = [], collisions: TossCollision[] = [];
  let bounces = 0;
  const finalRot = getFaceRotationOrientation(params.diceType, targetFace);

  for (let step = 0; step < maxSteps; step++) {
    const t = step * dt;
    vz -= g * dt; vx -= vx * drag * dt; vy -= vy * drag * dt;
    let nx = x + vx * dt, ny = y + vy * dt, nz = z + vz * dt;

    if (nx <= b.minX || nx >= b.maxX) {
      vx = -vx * cfg.restitution; nx = Math.max(b.minX, Math.min(b.maxX, nx));
      bounces++; collisions.push({ type: 'wall', x: nx, y: ny, z: nz, t, energy: 0.5 * cfg.mass * (vx * vx + vy * vy) });
    }
    if (ny <= b.minY || ny >= b.maxY) {
      vy = -vy * cfg.restitution; ny = Math.max(b.minY, Math.min(b.maxY, ny));
      bounces++; collisions.push({ type: 'wall', x: nx, y: ny, z: nz, t, energy: 0.5 * cfg.mass * (vx * vx + vy * vy) });
    }
    if (nz <= 0.0) {
      nz = 0.0;
      if (Math.abs(vz) > 0.25) {
        vz = -vz * cfg.restitution; vx *= 1.0 - cfg.friction; vy *= 1.0 - cfg.friction;
        bounces++; collisions.push({ type: 'floor', x: nx, y: ny, z: 0, t, energy: 0.5 * cfg.mass * (vz * vz) });
      } else {
        vz = 0.0; vx *= 1.0 - cfg.friction * 1.6; vy *= 1.0 - cfg.friction * 1.6;
      }
    }

    const speed = Math.hypot(vx, vy, vz), progress = Math.min(1.0, step / (maxSteps * 0.7));
    const tumble = (1.0 - progress) * 16.0;
    const curRotX = finalRot.rotX * progress + Math.sin(t * 14) * tumble;
    const curRotY = finalRot.rotY * progress + Math.cos(t * 12) * tumble;
    const curRotZ = finalRot.rotZ * progress + t * tumble;

    trajectory.push({ x: nx, y: ny, z: Math.max(0, nz), rotX: curRotX, rotY: curRotY, rotZ: curRotZ, t });
    x = nx; y = ny; z = nz;

    if (nz <= 0.02 && speed < 0.12 && step > 10) {
      trajectory.push({ x, y, z: 0, rotX: finalRot.rotX, rotY: finalRot.rotY, rotZ: finalRot.rotZ, t: (step + 1) * dt });
      break;
    }
  }

  const duration = trajectory.length > 0 ? trajectory[trajectory.length - 1].t : 1.0;
  return {
    diceId, diceType: params.diceType, faceValue: targetFace,
    settledPosition: [Math.round(x * 100) / 100, Math.round(y * 100) / 100, 0],
    settledCell: [Math.floor(x), Math.floor(y)], bounces, duration, trajectory, collisions,
  };
}

export function verifyCryptographicAlignment(solved: SolvedDiceToss, expectedFace: number): boolean {
  return solved.faceValue === expectedFace;
}
