/**
 * App Shell Absentee Drawer Actions (TASK-0954).
 *
 * The stance drawer shows the real stand-in state and the stored stance. Opening it reads both from
 * the gateway: the session state for the caller seat, and the stored policy (TASK-0974). Saving a
 * stance writes it through the guardrail route. The drawer never shows a stand-in status or a stance
 * that the server did not return.
 */

import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import { saveStandInPolicyChange } from './stand-in-policy.ts';

/**
 * Opens the stance drawer for the bound character after the gateway reads its stand-in state.
 * The drawer stays closed when the route changed during the reads, for example when the player
 * marks the seat absent in the lobby and then goes to the session view.
 */
export async function openAbsenteeDrawer(host: RunefobleApp): Promise<void> {
  const startRoute = host.currentRoute;
  const charId = host.activeCharacter?.id;
  if (!charId) {
    host.showToast('Stance drawer not opened. No character is bound to this session.');
    return;
  }
  const [session, policy] = await Promise.all([
    appDataService.fetchSessionState(host.sessionId),
    appDataService.fetchCharacterGuardrails(charId),
  ]);
  if (host.currentRoute !== startRoute) return;
  if (!session.ok) {
    host.showToast(`Stance drawer not opened. ${session.message}`);
    return;
  }
  if (!policy.ok) {
    host.showToast(`Stance drawer not opened. ${policy.message}`);
    return;
  }
  host.sessionParticipants = session.data.participants;
  host.absenteeStance = typeof policy.data.stance === 'string' ? policy.data.stance : '';
  host.isAbsenteeDirectiveOpen = true;
}

/** Saves the stance that the drawer selected. The drawer shows the new stance only after the save. */
export async function saveAbsenteeStance(host: RunefobleApp, stance: string): Promise<void> {
  const charId = host.activeCharacter?.id;
  if (!charId) return;
  const saved = await saveStandInPolicyChange(charId, { stance });
  if (!saved.ok) {
    host.showToast(`Stance not saved. ${saved.message}`);
    return;
  }
  host.absenteeStance = stance;
  host.showToast(`Tactical stance saved: ${stance}`);
}
