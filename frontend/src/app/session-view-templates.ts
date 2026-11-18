/**
 * App Shell Session and Character Sheet Templates (TASK-0640b).
 *
 * Renders the live VTT view, the spectator view, the character sheet route, and the
 * absentee stand-in overlays. Event handlers call the App Shell host and the VTT handlers.
 */

import { html } from 'lit';
import type { RunefobleApp } from '../runefoble-app.ts';
import { router } from '../router/index.ts';
import { handleSheetAddItem, handleSheetApplyCondition, handleSheetCastSpell, handleSheetEquipItem, handleSheetExpendSlot, handleSheetHpChange, handleSheetPrepareSpell, handleSheetRemoveCondition, handleSheetRemoveItem, handleSheetRestoreSlot, handleSheetUnequipItem } from '../character-sheet-handlers.ts';
import { appDataService } from '../services/app-data-service.ts';

/** Renders the live tabletop (party mode) or the spectator view for an active session. */
export function renderSessionActive(app: RunefobleApp) {
  const char = app.activeCharacter ?? app.resolveActiveCharacter(app.campaignId);
  const isOwnerOrDm = app.isDM || app.currentCampaign?.role === 'owner' || app.currentCampaign?.role === 'dm';
  if (app.viewMode === 'spectator') {
    return html`<runefoble-spectator-view .sessionId=${app.sessionId} .cols=${app.boardCols} .rows=${app.boardRows} .tokens=${app.tokens} .atmosphere=${app.atmosphere} .chronicle=${app.events}></runefoble-spectator-view>`;
  }
  return html`<div class="layout-grid">
    <div class="board-column">
      <runefoble-plugin-slot slot-id="hud-widget" .showFallback=${false}></runefoble-plugin-slot>
      <runefoble-board .cols=${app.boardCols} .rows=${app.boardRows} .tokens=${app.tokens} .fogOfWar=${true} .websocketUrl=${app.getWebSocketUrl()} @token-action=${(e: CustomEvent) => app.handleBoardTokenAction(e)} @aoe-place=${(e: CustomEvent) => app.handleBoardAoEPlace(e)} @spell-vfx-triggered=${(e: CustomEvent) => app.handleBoardSpellVFX(e)} @confirm-ghost=${(e: CustomEvent) => app.handleBoardConfirmGhost(e)}></runefoble-board>
    </div>
    <div class="character-column">
      ${isOwnerOrDm ? html`<div class="dm-party-inspector" role="region" aria-label="DM Party Inspector"><span class="dm-badge">DM Party Inspector</span><select class="dm-character-switcher" aria-label="Switch inspected character" @change=${(e: Event) => app.handleDmSwitchCharacter((e.target as HTMLSelectElement).value)}>${app.characters.map((c) => html`<option value="${c.id}" ?selected=${c.id === char?.id}>${c.name} (${c.characterClass} Lv ${c.level})</option>`)}</select></div>` : ''}
      ${char ? html`<runefoble-character-card .characterName=${char.name} .characterClass=${`${char.characterClass}${char.level ? ` Lvl ${char.level}` : ''}`} .level=${char.level} .currentHp=${char.currentHp} .maxHp=${char.maxHp} .armorClass=${char.armorClass} .portraitUrl=${char.portraitUrl || ''} .isAiStandIn=${Boolean(char.isAiStandIn)}></runefoble-character-card>
      <button class="btn-toggle-directive" @click=${() => { app.isAbsenteeDirectiveOpen = true; }}>📋 Stance Directives</button>` : html`<div class="empty-state" data-testid="active-character-empty"><p>No character is bound to this session. Choose a character in the session lobby.</p></div>`}
      <runefoble-plugin-slot slot-id="sidebar-tool" .showFallback=${false}></runefoble-plugin-slot>
      <runefoble-plugin-slot slot-id="dice-panel" .showFallback=${false}></runefoble-plugin-slot>
    </div>
    <runefoble-watcher-feed .events=${app.events}></runefoble-watcher-feed>
  </div>
  <div class="voice-container">
    <runefoble-voice-controls .isListening=${app.isListening} @voice-toggle=${() => { app.isListening = !app.isListening; }}></runefoble-voice-controls>
  </div>`;
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
    <runefoble-stand-in-guardrails .characterId=${charId} .characterName=${char.name ?? ''} .preserveSpellSlots=${preserveSlots} .protectAllies=${protectAllies} .protectAllyHpThreshold=${protectAllyHpThreshold} .riskThreshold=${riskThreshold} .avoidMelee=${avoidMelee} .permadeathSafeguard=${permadeathSafeguard} .customPriorities=${customPriorities} @guardrails-saved=${async (e: CustomEvent) => { await appDataService.updateCharacterGuardrails(charId, e.detail); app.showToast('Tactical Guardrails Saved!'); if (app.selectedCharacter) { app.selectedCharacter = { ...app.selectedCharacter, stand_in_guardrails: e.detail, standInGuardrails: e.detail }; } }} @hot-swap-requested=${async (e: CustomEvent) => { const cId = e.detail?.characterId || charId; await appDataService.requestHotSwap(app.sessionId, cId, app.currentUserId); app.showToast('Hot-Swap Takeover Requested: Control transferred to player!'); }}></runefoble-stand-in-guardrails>
  </div>`;
}

/** Renders the absentee stance drawer when it is open. The drawer needs a bound character. */
export function renderAbsenteeOverlays(app: RunefobleApp) {
  const active = app.activeCharacter;
  if (!app.isAbsenteeDirectiveOpen || !active) return html``;
  return html`<div class="absentee-modal-backdrop" @click=${() => { app.isAbsenteeDirectiveOpen = false; }}>
    <div class="absentee-drawer" @click=${(e: Event) => e.stopPropagation()}>
      <div class="modal-top-bar"><h3>Tactical Stance Directives</h3><button class="btn-close-modal" @click=${() => { app.isAbsenteeDirectiveOpen = false; }}>✕ Close</button></div>
      <runefoble-absentee-directive .characterName=${active.name ?? ''} .characterClass=${active.characterClass ?? ''} .standInActive=${true} .currentHp=${active.currentHp ?? 0} .maxHp=${active.maxHp ?? 0} @directive-changed=${(e: CustomEvent) => { app.showToast(`Tactical directive updated: ${e.detail?.stance}`); }}></runefoble-absentee-directive>
    </div>
  </div>`;
}
