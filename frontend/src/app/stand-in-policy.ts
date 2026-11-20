/**
 * App Shell Stand-In Policy Writes (TASK-0954).
 *
 * The guardrail PUT replaces the whole policy. A save that changes one field therefore reads the
 * stored policy first, applies the change, and sends the result. A failed read or write returns
 * the failure. Nothing is reported as saved until the gateway confirms the write.
 */

import { appDataService } from '../services/app-data-service.ts';
import { dataOk, type DataResult } from '../services/data-result.ts';

/** Saves a change to the stored stand-in policy. Returns the policy the server accepted. */
export async function saveStandInPolicyChange(characterId: string, change: Record<string, unknown>): Promise<DataResult<Record<string, unknown>>> {
  const stored = await appDataService.fetchCharacterGuardrails(characterId);
  if (!stored.ok) return stored;
  const policy = { ...stored.data, ...change };
  const saved = await appDataService.updateCharacterGuardrails(characterId, policy);
  return saved.ok ? dataOk(policy) : saved;
}
