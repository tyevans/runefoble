/**
 * Presentation helpers for AoE templates. Containment is server-owned
 * (board_state.geometry). The client never computes affected cells or tokens.
 */

export const CONE_SPREAD_DEG = 53.13; // Standard 5e cone spread angle, used for drawing only

export function snapAngle(deg: number, increment = 15): number {
  if (increment <= 0) return ((deg % 360) + 360) % 360;
  const snapped = Math.round(deg / increment) * increment;
  return ((snapped % 360) + 360) % 360;
}
