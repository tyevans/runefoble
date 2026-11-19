/**
 * Infrastructure faults for e2e journeys (TASK-0909).
 *
 * A step stops an owning service on Kind with a public make target. The target scales the
 * deployment to 0 and waits until the gateway `/healthz` reports the service as unreachable.
 * The restart target scales it back to 1 and waits until the gateway reports it operational.
 * This changes no data and fakes no reply (ADR-0014). Source: `scripts/e2e_service_fault.py`.
 */

import { execFileSync } from 'node:child_process';

/** The services that a journey can stop, with their make target stem. */
const FAULT_TARGETS = {
  campaign_lore: 'e2e-lore',
  game_session: 'e2e-game-session',
} as const;

export type FaultService = keyof typeof FAULT_TARGETS;

/** Runs a public make target from the repository root. A failed target throws with its output. */
function runMakeTarget(target: string): void {
  try {
    execFileSync('make', [target], { cwd: process.cwd(), stdio: 'pipe' });
  } catch (error) {
    const output = error instanceof Error && 'stderr' in error ? String((error as { stderr: unknown }).stderr) : '';
    throw new Error(`make ${target} failed. ${output}`);
  }
}

/** Stops the service and returns when the gateway reports it unreachable. */
export function stopService(service: FaultService): void {
  runMakeTarget(`${FAULT_TARGETS[service]}-down`);
}

/** Starts the service and returns when the gateway reports it operational. */
export function startService(service: FaultService): void {
  runMakeTarget(`${FAULT_TARGETS[service]}-up`);
}
