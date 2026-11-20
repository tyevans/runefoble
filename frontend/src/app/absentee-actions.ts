/**
 * App Shell Absentee Drawer Actions (TASK-0954).
 *
 * The stance drawer shows the real stand-in state and the stored stance. Opening it reads both from
 * the gateway. Saving a stance writes it through the guardrail route. The drawer never shows a
 * stand-in status or a stance that the server did not return.
 */

import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import { saveStandInPolicyChange } from './stand-in-policy.ts';

/** Opens the stance drawer for the bound character after the gateway reads its stand-in state. */
export async function openAbsenteeDrawer(host: RunefobleApp): Promise<void> {
  const charId = host.activeCharacter?.id;
  if (!charId) {
    host.showToast('Stance drawer not opened. No character is bound to this session.');
    return;
  }
  const [character, policy] = await Promise.all([
    appDataService.fetchCharacter(charId),
    appDataService.fetchCharacterGuardrails(charId),
  ]);
  if (!character.ok) {
    host.showToast(`Stance drawer not opened. ${character.message}`);
    return;
  }
  if (!policy.ok) {
    host.showToast(`Stance drawer not opened. ${policy.message}`);
    return;
  }
  const isAiStandIn = Boolean(character.data.isAiStandIn ?? character.data.is_stand_in_active);
  const bound = host.activeCharacter;
  if (bound) host.activeCharacter = { ...bound, isAiStandIn };
  host.characters = host.characters.map((c) => (c.id === charId ? { ...c, isAiStandIn } : c));
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
