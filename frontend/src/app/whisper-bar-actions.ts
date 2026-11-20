/**
 * App Shell host of the DM whisper bar (TASK-0949).
 *
 * The bar sends `action-vetoed` when the DM clicks Veto. The shell posts the veto route through
 * the gateway. A 200 reply marks the action as vetoed in the bar, so the pause window ends with
 * no board change. A refusal shows the owner's reason in the bar. The shell shows no optimistic
 * result.
 */

import type { ActionVetoedDetail, RunefobleDmWhisperBar } from '@runefoble/the-watcher-ui';
import { appDataService } from '../services/app-data-service.ts';

/** The plugin id of the whisper bar in the `sidebar-tool` slot. */
export const WHISPER_BAR_PLUGIN_ID = 'default-dm-whisper-bar';

/** The props that the slot sets on the whisper bar: the ids of the open session. */
export function whisperBarProps(sessionId: string, campaignId: string): Record<string, Record<string, unknown>> {
  return { [WHISPER_BAR_PLUGIN_ID]: { sessionId, campaignId } };
}

/** Posts the veto of the event's action. Reports the result to the bar that sent the event. */
export async function handleActionVetoed(e: Event): Promise<void> {
  const bar = e.composedPath()[0] as RunefobleDmWhisperBar;
  const veto = (e as CustomEvent<ActionVetoedDetail>).detail;
  const res = await appDataService.vetoWatcherAction(veto);
  if (res.ok) bar.markActionVetoed(veto.actionId);
  else bar.showActionError(`Veto failed: ${res.message}`);
}
