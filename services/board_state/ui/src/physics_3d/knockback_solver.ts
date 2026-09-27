/**
 * Directional Impulse Vector Solver for 3D Miniature Tokens (TASK-0171).
 * Calculates force vectors, mass scaling, deceleration sliding friction, and obstacle rebounds.
 */

export interface KnockbackParams {
  tokenId: string;
  fromX: number;
  fromY: number;
  fromZ?: number;
  directionX: number;
  directionY: number;
  distanceFt?: number;
  mass?: number;
  friction?: number;
  restitution?: number;
  bounds?: { cols: number; rows: number };
  walls?: Array<{ x: number; y: number }>;
  tokens?: Array<{ id: string; x: number; y: number; radius?: number }>;
}

export interface KnockbackPoint {
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  t: number;
  tiltX: number;
  tiltY: number;
}

export interface SolvedKnockback {
  tokenId: string;
  fromX: number;
  fromY: number;
  fromZ: number;
  toX: number;
  toY: number;
  toZ: number;
  distanceFt: number;
  collided: boolean;
  collisionType?: 'wall' | 'boundary' | 'token';
  collisionPoint?: [number, number, number];
  impactEnergy: number;
  reboundVector?: { x: number; y: number };
  trajectory: KnockbackPoint[];
  duration: number;
}

export function solveKnockbackTrajectory(params: KnockbackParams): SolvedKnockback {
  const mass = Math.max(0.1, params.mass ?? 1.0);
  const friction = params.friction ?? 0.35;
  const restitution = params.restitution ?? 0.35;
  const cols = params.bounds?.cols ?? 8, rows = params.bounds?.rows ?? 8;
  const mag = Math.hypot(params.directionX, params.directionY) || 1.0;
  const dx = params.directionX / mag, dy = params.directionY / mag;

  const baseDist = Math.max(1.0, params.distanceFt ?? 10.0);
  const massScaledDist = baseDist / Math.sqrt(mass);
  const v = (massScaledDist / 5.0) * 3.5;
  let vx = dx * v, vy = dy * v;
  let x = params.fromX, y = params.fromY;
  const z = params.fromZ ?? 0.0;

  const dt = 0.02, maxSteps = 150;
  const trajectory: KnockbackPoint[] = [];
  let collided = false;
  let colType: 'wall' | 'boundary' | 'token' | undefined;
  let colPt: [number, number, number] | undefined;
  let impactEnergy = 0.0;
  let reboundVec: { x: number; y: number } | undefined;

  for (let step = 0; step < maxSteps; step++) {
    const t = Math.round(step * dt * 1000) / 1000;
    const speed = Math.hypot(vx, vy);
    const tiltScale = Math.min(0.35, speed * 0.06);
    trajectory.push({
      x: Math.round(x * 1000) / 1000,
      y: Math.round(y * 1000) / 1000,
      z, vx: Math.round(vx * 100) / 100, vy: Math.round(vy * 100) / 100,
      t, tiltX: Math.round(-dx * tiltScale * 1000) / 1000,
      tiltY: Math.round(-dy * tiltScale * 1000) / 1000,
    });

    if (speed < 0.05) break;

    const nx = x + vx * dt, ny = y + vy * dt;
    if (nx < 0.2 || nx > cols - 0.8 || ny < 0.2 || ny > rows - 0.8) {
      collided = true; colType = 'boundary';
      colPt = [Math.round(x * 100) / 100, Math.round(y * 100) / 100, z];
      impactEnergy = Math.round(0.5 * mass * speed * speed * 100) / 100;
      reboundVec = { x: -vx * restitution, y: -vy * restitution };
      break;
    }

    const cellX = Math.floor(nx), cellY = Math.floor(ny);
    if (params.walls?.some(w => w.x === cellX && w.y === cellY)) {
      collided = true; colType = 'wall';
      colPt = [cellX, cellY, z];
      impactEnergy = Math.round(0.5 * mass * speed * speed * 100) / 100;
      reboundVec = { x: -vx * restitution, y: -vy * restitution };
      break;
    }

    const hitTok = params.tokens?.find(tok => tok.id !== params.tokenId && Math.hypot(tok.x - nx, tok.y - ny) < (tok.radius ?? 0.6));
    if (hitTok) {
      collided = true; colType = 'token';
      colPt = [hitTok.x, hitTok.y, z];
      impactEnergy = Math.round(0.5 * mass * speed * speed * 100) / 100;
      reboundVec = { x: -vx * restitution, y: -vy * restitution };
      break;
    }

    const decel = friction * 9.81 * dt;
    vx -= (vx / speed) * decel;
    vy -= (vy / speed) * decel;
    x = nx; y = ny;
  }

  const duration = trajectory.length > 0 ? trajectory[trajectory.length - 1].t : 0.0;
  return {
    tokenId: params.tokenId,
    fromX: params.fromX, fromY: params.fromY, fromZ: z,
    toX: Math.round(x * 100) / 100, toY: Math.round(y * 100) / 100, toZ: z,
    distanceFt: Math.round(Math.hypot(x - params.fromX, y - params.fromY) * 50) / 10,
    collided, collisionType: colType, collisionPoint: colPt,
    impactEnergy, reboundVector: reboundVec, trajectory, duration,
  };
}
