/**
 * Character Views (TASK-0643). The global roster and the character sheet route.
 */

import { html } from 'lit';
import { router } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import type { InspectCharacterEventDetail } from '@runefoble/character-sheet-ui';
import type { MatchedRoute } from '../router/index.ts';
import { appDataService } from '../services/app-data-service.ts';
import { failLoad } from '../app/load-error.ts';
import { handleSheetAddItem, handleSheetApplyCondition, handleSheetCastSpell, handleSheetEquipItem, handleSheetExpendSlot, handleSheetHpChange, handleSheetPrepareSpell, handleSheetRemoveCondition, handleSheetRemoveItem, handleSheetRestoreSlot, handleSheetUnequipItem } from '../character-sheet-handlers.ts';
import { assignCharacterFromEvent, createCharacterFromEvent, deleteCharacterFromEvent } from '../app/character-actions.ts';

/** Opens the character sheet route for the inspected character. */
export function inspectCharacterFromEvent(e: CustomEvent<InspectCharacterEventDetail>): void {
  router.navigate('#/characters/' + e.detail.characterId);
}

export async function loadRoster(host: RunefobleApp): Promise<void> {
  const [chars, rosterCamps] = await Promise.all([appDataService.fetchCharacters(), appDataService.fetchRosterCampaignOptions()]);
  if (!chars.ok || !rosterCamps.ok) return failLoad(host, chars, rosterCamps);
  host.characters = chars.data;
  host.rosterCampaigns = rosterCamps.data;
}

export async function loadCharacterSheet(host: RunefobleApp, route: MatchedRoute): Promise<void> {
  const charId = route.params.characterId ?? '';
  host.selectedCharacterId = charId;
  host.selectedCharacter = null;
  const res = await appDataService.fetchCharacter(charId);
  if (!res.ok) return failLoad(host, res);
  host.selectedCharacter = res.data;
  if (host.selectedCharacter?.name) {
    router.setRouteTitle('character:' + charId, host.selectedCharacter.name);
    host.breadcrumbs = router.getCurrentRoute()?.breadcrumbs || host.breadcrumbs;
  }
}

export function renderRoster(app: RunefobleApp) {
  return html`<runefoble-character-roster .characters=${app.characters} .campaigns=${app.rosterCampaigns} current-user-id=${app.currentUserId} @create-character=${(e: CustomEvent) => createCharacterFromEvent(app, e)} @assign-campaign=${(e: CustomEvent) => assignCharacterFromEvent(app, e)} @delete-character=${(e: CustomEvent) => deleteCharacterFromEvent(app, e)} @inspect-character=${(e: CustomEvent) => inspectCharacterFromEvent(e)}></runefoble-character-roster>`;
}

/** Renders the character sheet route. A missing record shows an empty state with a create action. */
export function renderCharacterSheet(app: RunefobleApp) {
  const char = app.selectedCharacter, charId = app.selectedCharacterId || app.routeParams.characterId || '';
  if (!char) {
    return html`<div class="character-sheet-view empty-state" data-testid="character-sheet-empty">
      <div class="character-sheet-header-bar"><button class="back-to-roster-btn" @click=${() => router.navigate('#/characters')}>← Back to Roster</button></div>
      <h2>No character sheet</h2>
      <p>This character has no sheet yet. Create a character to start one.</p>
      <button class="create-character-btn" @click=${() => router.navigate('#/characters')}>Create character</button>
    </div>`;
  }
  const g = char.stand_in_guardrails || char.standInGuardrails || {};
  const preserveSlots = g.preserve_spell_slots || g.preserveSpellSlots || {};
  const protectAllies: string[] = g.protect_allies || g.protectAllies || [];
  const protectAllyHpThreshold = g.protect_ally_hp_threshold ?? g.protectAllyHpThreshold ?? 0;
  const riskThreshold = g.risk_threshold || g.riskThreshold || '';
  const avoidMelee = g.avoid_melee ?? g.avoidMelee ?? false, permadeathSafeguard = g.permadeath_safeguard ?? g.permadeathSafeguard ?? false;
  const customPriorities: string[] = g.custom_priorities || g.customPriorities || [];
  return html`<div class="character-sheet-view">
    <div class="character-sheet-header-bar"><button class="back-to-roster-btn" @click=${() => router.navigate('#/characters')}>← Back to Roster</button></div>
    <runefoble-character-sheet .characterId=${charId} .characterName=${char.name ?? ''} .characterClass=${char.characterClass || char.character_class || ''} .level=${char.level ?? 0} .currentHp=${char.currentHp ?? char.current_hp ?? 0} .maxHp=${char.maxHp ?? char.max_hp ?? 0} .armorClass=${char.armorClass ?? char.armor_class ?? 0} .speed=${char.speed ?? char.speed_ft ?? 0} .isAiStandIn=${Boolean(char.isAiStandIn ?? char.is_stand_in_active)} .equipment=${char.equipment || {}} .inventory=${Array.isArray(char.inventory) ? char.inventory : Object.values(char.inventory || {})} .conditions=${Array.isArray(char.conditions) ? char.conditions : Object.entries(char.conditions || {}).map(([k, val]: [string, any]) => ({ id: k, name: val.condition || k, source: val.source || 'tactical', description: val.source || 'Tactical condition' }))} .penalties=${char.penalties || {}} .spellSlots=${char.spellSlots || char.spell_slots || {}} .maxSpellSlots=${char.maxSpellSlots || char.max_spell_slots || char.spell_slots || {}} .preparedSpells=${char.preparedSpells || char.prepared_spells || []} .spellbook=${char.spellbook || []} @hp-change=${(e: CustomEvent) => handleSheetHpChange(app, charId, e)} @equip-item=${(e: CustomEvent) => handleSheetEquipItem(app, charId, e)} @unequip-item=${(e: CustomEvent) => handleSheetUnequipItem(app, charId, e)} @add-item=${(e: CustomEvent) => handleSheetAddItem(app, charId, e)} @remove-item=${(e: CustomEvent) => handleSheetRemoveItem(app, charId, e)} @cast-spell=${(e: CustomEvent) => handleSheetCastSpell(app, charId, e)} @prepare-spell=${(e: CustomEvent) => handleSheetPrepareSpell(app, charId, e)} @apply-condition=${(e: CustomEvent) => handleSheetApplyCondition(app, charId, e)} @remove-condition=${(e: CustomEvent) => handleSheetRemoveCondition(app, charId, e)} @expend-slot=${(e: CustomEvent) => handleSheetExpendSlot(app, charId, e)} @restore-slot=${(e: CustomEvent) => handleSheetRestoreSlot(app, charId, e)}></runefoble-character-sheet>
    <runefoble-stand-in-guardrails .characterId=${charId} .characterName=${char.name ?? ''} .preserveSpellSlots=${preserveSlots} .protectAllies=${protectAllies} .protectAllyHpThreshold=${protectAllyHpThreshold} .riskThreshold=${riskThreshold} .avoidMelee=${avoidMelee} .permadeathSafeguard=${permadeathSafeguard} .customPriorities=${customPriorities} @guardrails-saved=${async (e: CustomEvent) => { await appDataService.updateCharacterGuardrails(charId, e.detail); app.showToast('Tactical Guardrails Saved!'); if (app.selectedCharacter) { app.selectedCharacter = { ...app.selectedCharacter, stand_in_guardrails: e.detail, standInGuardrails: e.detail }; } }} @hot-swap-requested=${async (e: CustomEvent) => { const cId = e.detail?.characterId || charId; await appDataService.requestHotSwap(app.sessionId, cId); app.showToast('Hot-Swap Takeover Requested: Control transferred to player!'); }}></runefoble-stand-in-guardrails>
  </div>`;
}
