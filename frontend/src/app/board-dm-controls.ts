/**
 * Board DM Controls for the App Shell (TASK-0685).
 *
 * The App Shell mounts the DM trap controls and the map switcher on the live board. The
 * board id is the session id, because the board stream and the board routes use the session.
 * The DM trap controls take their target cell from the board move dispatch.
 *
 * The board service checks the DM permission on each request. This check only shapes the view.
 */

import type { RunefobleApp } from '../runefoble-app.ts';
import type { CampaignCapabilities } from '../services/campaign-capabilities.ts';

export interface BoardTarget {
  targetX: number;
  targetY: number;
}

export type BoardDmAccess = 'allowed' | 'denied';

/** Returns `allowed` only when the caller holds the `run_session` capability (TASK-0559). A missing flag denies access. */
export function resolveBoardDmAccess(capabilities: Partial<Pick<CampaignCapabilities, 'run_session'>> | null | undefined): BoardDmAccess {
  return capabilities?.run_session === true ? 'allowed' : 'denied';
}

/**
 * Returns the destination cell of a `move-token` dispatch. A missing, fractional, or negative
 * coordinate returns null. The App Shell never guesses a cell.
 */
export function targetFromMoveDispatch(detail: { toX?: unknown; toY?: unknown } | null | undefined): BoardTarget | null {
  const x = detail?.toX;
  const y = detail?.toY;
  if (!isGridCoordinate(x) || !isGridCoordinate(y)) return null;
  return { targetX: x, targetY: y };
}

/** Stores the destination cell of a move dispatch as the DM controls target. */
export function recordBoardMoveTarget(host: RunefobleApp, event: CustomEvent): void {
  const target = targetFromMoveDispatch(event.detail);
  if (target) host.boardTarget = target;
}

function isGridCoordinate(value: unknown): value is number {
  return Number.isInteger(value) && (value as number) >= 0;
}
