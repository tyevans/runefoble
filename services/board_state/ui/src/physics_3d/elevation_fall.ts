/**
 * Elevation Step & Ledge Gravity Fall Solver for 3D Miniature Tokens (TASK-0171).
 * Raycast heightfield collision dropping miniatures down vertical elevation steps
 * with rotational tilt damping and upright balance recovery.
 */

export interface ElevationFallParams {
  tokenId: string;
  fromZ: number;
  targetZ: number;
  gravity?: number;
  tiltDamping?: number;
  impactBounce?: number;
  initialTilt?: number;
}

export interface ElevationKeyframe {
  z: number;
  vz: number;
  tiltAngle: number;
  isAirborne: boolean;
  t: number;
}

export interface SolvedElevationFall {
  tokenId: string;
  fromZ: number;
  landedZ: number;
  fallHeight: number;
  impactVelocity: number;
  maxTiltAngle: number;
  duration: number;
  trajectory: ElevationKeyframe[];
  recoveredUpright: boolean;
}

export function solveElevationFall(params: ElevationFallParams): SolvedElevationFall {
  const g = params.gravity ?? 14.0;
  const tiltDamping = params.tiltDamping ?? 7.0;
  const bounce = params.impactBounce ?? 0.2;
  const fallHeight = Math.max(0.0, params.fromZ - params.targetZ);

  if (fallHeight <= 0.01) {
    return {
      tokenId: params.tokenId,
      fromZ: params.fromZ,
      landedZ: params.targetZ,
      fallHeight: 0,
      impactVelocity: 0,
      maxTiltAngle: 0,
      duration: 0,
      trajectory: [{ z: params.targetZ, vz: 0, tiltAngle: 0, isAirborne: false, t: 0 }],
      recoveredUpright: true,
    };
  }

  const dt = 0.02;
  const trajectory: ElevationKeyframe[] = [];
  let z = params.fromZ;
  let vz = 0.0;
  let t = 0.0;
  const baseTilt = params.initialTilt ?? Math.min(0.45, fallHeight * 0.2);
  let maxTilt = baseTilt;

  // Phase 1: Airborne fall under gravity
  while (z > params.targetZ && t < 2.0) {
    const tilt = Math.min(0.5, baseTilt + Math.abs(vz) * 0.03);
    trajectory.push({
      z: Math.round(z * 1000) / 1000,
      vz: Math.round(vz * 100) / 100,
      tiltAngle: Math.round(tilt * 1000) / 1000,
      isAirborne: true,
      t: Math.round(t * 1000) / 1000,
    });
    vz -= g * dt;
    z += vz * dt;
    t += dt;
  }

  // Phase 2: Landing impact & Upright balance recovery
  const impactVel = Math.abs(vz);
  z = params.targetZ;
  const bounceVz = Math.abs(vz) * bounce;
  const landingTime = t;

  const recoverySteps = 25;
  for (let i = 0; i <= recoverySteps; i++) {
    const recT = i * dt;
    const curT = landingTime + recT;
    const decay = Math.exp(-tiltDamping * recT);
    const tilt = baseTilt * decay * Math.cos(15 * recT);
    if (Math.abs(tilt) > maxTilt) maxTilt = Math.abs(tilt);
    const curZ = Math.max(params.targetZ, params.targetZ + (recT < 0.08 ? bounceVz * (0.08 - recT) : 0));

    trajectory.push({
      z: Math.round(curZ * 1000) / 1000,
      vz: Math.round((recT < 0.08 ? bounceVz : 0) * 100) / 100,
      tiltAngle: Math.round(tilt * 1000) / 1000,
      isAirborne: false,
      t: Math.round(curT * 1000) / 1000,
    });
  }

  const finalT = trajectory.length > 0 ? trajectory[trajectory.length - 1].t : t;
  const lastTilt = trajectory.length > 0 ? trajectory[trajectory.length - 1].tiltAngle : 0;
  return {
    tokenId: params.tokenId,
    fromZ: params.fromZ,
    landedZ: params.targetZ,
    fallHeight: Math.round(fallHeight * 100) / 100,
    impactVelocity: Math.round(impactVel * 100) / 100,
    maxTiltAngle: Math.round(maxTilt * 1000) / 1000,
    duration: Math.round(finalT * 1000) / 1000,
    trajectory,
    recoveredUpright: Math.abs(lastTilt) < 0.02,
  };
}
