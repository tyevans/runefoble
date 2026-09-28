import { html } from 'lit';
import type { RunefobleStandInGuardrails } from './runefoble-stand-in-guardrails.ts';

export function renderHeader(host: RunefobleStandInGuardrails) {
  return html`
    <div class="header">
      <div>
        <h3>🛡️ Stand-In Tactical Guardrails</h3>
        <div class="subtext">Playstyle constraints & zero-HP protection for <strong>${host.characterName || 'Hero'}</strong></div>
      </div>
      <button class="btn btn-takeover" @click=${() => host.handleHotSwap()}>⚡ Take Control (Hot-Swap)</button>
    </div>
  `;
}

export function renderSpellSlotPreservation(host: RunefobleStandInGuardrails) {
  return html`
    <div class="section">
      <div class="section-title">✨ Spell Slot Preservation</div>
      <div class="toggle-row">
        <div><div class="toggle-label">Reserve Level 3 Slots (Revivify)</div><div class="toggle-desc">Stand-in will not cast level 3 spells unless explicitly ordered</div></div>
        <input type="checkbox" .checked=${Boolean(host.preserveSpellSlots[3])} @change=${(e: Event) => {
          const slots = { ...host.preserveSpellSlots };
          if ((e.target as HTMLInputElement).checked) slots[3] = 1; else delete slots[3];
          host.preserveSpellSlots = slots;
        }} />
      </div>
    </div>
  `;
}

export function renderSliderControls(host: RunefobleStandInGuardrails) {
  const pct = Math.round(host.protectAllyHpThreshold * 100);
  return html`
    <div style="margin-top: 10px;">
      <div class="toggle-label">Protection HP Threshold (${pct}%)</div>
      <div class="slider-row">
        <input type="range" min="0.1" max="0.9" step="0.05" .value=${String(host.protectAllyHpThreshold)}
          @input=${(e: Event) => (host.protectAllyHpThreshold = parseFloat((e.target as HTMLInputElement).value))} />
        <span class="slider-val">${pct}% HP</span>
      </div>
    </div>
  `;
}

export function renderAllyProtectionTags(host: RunefobleStandInGuardrails) {
  return html`
    <div class="section">
      <div class="section-title">🤝 Party Member Protection Affinities</div>
      <div class="chips-container">${host.protectAllies.map((ally, idx) => html`<span class="chip"><span>🛡️ ${ally}</span><span class="chip-remove" @click=${() => host.removeAlly(idx)}>×</span></span>`)}</div>
      <div class="input-row">
        <input type="text" placeholder="Add ally name (e.g. Marcus)" .value=${host.newAllyInput}
          @input=${(e: Event) => (host.newAllyInput = (e.target as HTMLInputElement).value)}
          @keydown=${(e: KeyboardEvent) => e.key === 'Enter' && host.addAlly()} />
        <button class="btn btn-secondary" @click=${() => host.addAlly()}>Add</button>
      </div>
      ${renderSliderControls(host)}
    </div>
  `;
}

export function renderPostureSelector(host: RunefobleStandInGuardrails) {
  return html`
    <div class="section">
      <div class="section-title">⚠️ Tactical Posture & Risk Thresholds</div>
      <div style="margin-bottom: 10px;">
        <div class="toggle-label" style="margin-bottom: 4px;">Risk Appetite</div>
        <select .value=${host.riskThreshold} @change=${(e: Event) => { host.riskThreshold = (e.target as HTMLSelectElement).value as 'cautious' | 'balanced' | 'reckless'; }}>
          <option value="cautious">Cautious (Favor Defense & Ranged)</option>
          <option value="balanced">Balanced (Standard Tactic)</option>
          <option value="reckless">Reckless (Aggressive Intervention)</option>
        </select>
      </div>
      <div class="toggle-row">
        <div><div class="toggle-label">Avoid Frontline Melee</div><div class="toggle-desc">Maintain safe tactical distance; favor ranged attacks and spells</div></div>
        <input type="checkbox" .checked=${host.avoidMelee} @change=${(e: Event) => (host.avoidMelee = (e.target as HTMLInputElement).checked)} />
      </div>
      <div class="toggle-row">
        <div><div class="toggle-label">Permadeath Safeguard (Zero-HP Stabilization)</div><div class="toggle-desc">Automatically stabilize at 0 HP without death save failures</div></div>
        <input type="checkbox" .checked=${host.permadeathSafeguard} @change=${(e: Event) => (host.permadeathSafeguard = (e.target as HTMLInputElement).checked)} />
      </div>
    </div>
  `;
}

export function renderCustomPriorityChips(host: RunefobleStandInGuardrails) {
  return html`
    <div class="section">
      <div class="section-title">📋 Custom Tactical Priorities</div>
      <div class="chips-container">${host.customPriorities.map((p, idx) => html`<span class="chip chip-priority"><span>⚡ ${p}</span><span class="chip-remove" @click=${() => host.removePriority(idx)}>×</span></span>`)}</div>
      <div class="input-row">
        <input type="text" placeholder="Add custom directive (e.g. Save slots for Revivify)" .value=${host.newPriorityInput}
          @input=${(e: Event) => (host.newPriorityInput = (e.target as HTMLInputElement).value)}
          @keydown=${(e: KeyboardEvent) => e.key === 'Enter' && host.addPriority()} />
        <button class="btn btn-secondary" @click=${() => host.addPriority()}>Add</button>
      </div>
    </div>
  `;
}

export function renderActionsBar(host: RunefobleStandInGuardrails) {
  return html`
    <div class="actions-bar">
      <span class="status-msg">${host.saveStatus}</span>
      <button class="btn" @click=${() => host.handleSave()}>Save Tactical Guardrails</button>
    </div>
  `;
}
