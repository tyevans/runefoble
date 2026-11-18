/**
 * App Shell Absentee Overlays (TASK-0643). Renders the absentee stance drawer when it is open.
 */

import { html } from 'lit';
import type { RunefobleApp } from '../runefoble-app.ts';

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
