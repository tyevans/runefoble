/**
 * App Shell Character Actions (TASK-0640b).
 *
 * Handles roster, lobby character selection, and DM inspector events.
 * A failed write shows a toast and leaves the roster unchanged.
 */

import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import type { AssignCampaignEventDetail, CreateCharacterPayload, DeleteCharacterEventDetail } from '@runefoble/character-sheet-ui';

export async function createCharacterFromEvent(host: RunefobleApp, e: CustomEvent<CreateCharacterPayload>): Promise<void> {
  const created = await appDataService.createCharacter(e.detail);
  if (!created.ok) {
    host.showToast(`Character not created. ${created.message}`);
    return;
  }
  const chars = await appDataService.fetchCharacters();
  if (chars.ok) host.characters = chars.data;
  else host.showToast(`Roster not refreshed. ${chars.message}`);
  if (!host.characters.some((c) => c.id === created.data.id)) host.characters = [created.data, ...host.characters];
  host.showToast(`Character "${created.data.name || e.detail.name}" created successfully`);
}

export async function assignCharacterFromEvent(host: RunefobleApp, e: CustomEvent<AssignCampaignEventDetail>): Promise<void> {
  const { characterId, campaignId, campaignTitle } = e.detail;
  const res = await appDataService.assignCharacterCampaign(characterId, campaignId);
  if (!res.ok) {
    host.showToast(`Campaign not changed. ${res.message}`);
    return;
  }
  host.characters = host.characters.map((c) => (c.id === characterId ? { ...c, campaignId, campaignTitle } : c));
  host.showToast(campaignId ? `Assigned to ${campaignTitle || 'campaign'}` : 'Unassigned from campaign');
}

export async function deleteCharacterFromEvent(host: RunefobleApp, e: CustomEvent<DeleteCharacterEventDetail>): Promise<void> {
  const res = await appDataService.deleteCharacter(e.detail.characterId);
  if (!res.ok) {
    host.showToast(`Character not deleted. ${res.message}`);
    return;
  }
  host.characters = host.characters.filter((c) => c.id !== e.detail.characterId);
  host.showToast('Character deleted successfully');
}

/** Binds a roster or lobby character choice to the participant and the active character. */
export function selectCharacterFromEvent(host: RunefobleApp, e: CustomEvent): void {
  const d = e.detail || {};
  const cId = d.characterId || (typeof d === 'string' ? d : null);
  if (!cId) return;
  const full = host.characters.find((c) => c.id === cId) || (d.character ? { id: d.character.id, name: d.character.name, characterClass: d.character.characterClass, level: d.character.level || 1, currentHp: 30, maxHp: 30, armorClass: 14, speed: 30, portraitUrl: d.character.portraitUrl || null } : null);
  if (full) host.activeCharacter = full;
  const s = host.activeCharacter;
  host.lobbyParticipants = host.lobbyParticipants.map((p) => (p.userId === (d.userId || host.currentUserId)
    ? { ...p, characterId: cId, characterName: s?.name || p.characterName, characterClass: s?.characterClass || p.characterClass, characterLevel: s?.level || p.characterLevel, portraitUrl: s?.portraitUrl || p.portraitUrl }
    : p));
}

/** Switches the DM inspector to another roster character. */
export function switchDmCharacter(host: RunefobleApp, cId: string): void {
  const f = host.characters.find((c) => c.id === cId);
  if (f) host.activeCharacter = f;
}
