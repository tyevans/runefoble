/**
 * App Shell Load Error (TASK-0640b).
 *
 * Stores the first failed read as the view load error. The shell then shows an error
 * state with retry instead of an empty view.
 */

import type { RunefobleApp } from '../runefoble-app.ts';
import type { DataFailure, DataResult } from '../services/data-result.ts';

/** Sets loadError to the first failed result. Clears it when every result succeeded. */
export function failLoad(host: RunefobleApp, ...results: DataResult<unknown>[]): void {
  host.loadError = results.find((r): r is DataFailure => !r.ok) ?? null;
}
