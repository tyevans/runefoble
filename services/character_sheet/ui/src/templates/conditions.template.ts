import { html } from 'lit';
import type { RunefobleCharacterSheet } from '../runefoble-character-sheet.ts';
import { KNOWN_CONDITION_DETAILS } from '../runefoble-character-sheet.types.ts';

function collectConditionBadges(sheet: RunefobleCharacterSheet) {
  const badges: { id: string; name: string; isPenalty: boolean; details: any }[] = [];
  sheet.conditions.forEach((c) => {
    const key = c.name.toLowerCase();
    const details = KNOWN_CONDITION_DETAILS[key] || {
      mechanics: c.description || 'Active condition.',
      savingThrowModifier: 'Standard',
      icon: c.source === 'session_penalty' ? '🍺' : '⚔️',
      isPenalty: c.source === 'session_penalty',
    };
    badges.push({ id: c.id, name: c.name, isPenalty: details.isPenalty || false, details });
  });
  Object.entries(sheet.penalties).forEach(([k, desc]) => {
    if (!badges.some((b) => b.name.toLowerCase() === k.toLowerCase())) {
      const details = KNOWN_CONDITION_DETAILS[k.toLowerCase()] || {
        mechanics: desc,
        savingThrowModifier: 'Modified by DM',
        icon: '🍺',
        isPenalty: true,
      };
      badges.push({ id: `pen-${k}`, name: k, isPenalty: true, details });
    }
  });
  return badges;
}

export function renderConditionsPanel(sheet: RunefobleCharacterSheet) {
  const allBadges = collectConditionBadges(sheet);
  return html`
    <div class="section-panel" style="margin-bottom:18px;">
      <div class="section-title">
        <span>⚡ Conditions & Penalties</span>
        <span style="font-size:0.75rem; color:var(--rf-text-muted);">${allBadges.length} Active</span>
      </div>
      <div class="conditions-grid">
        ${allBadges.length === 0
          ? html`<div style="font-size:0.8rem; color:var(--rf-text-muted); font-style:italic;">No active conditions or penalties.</div>`
          : allBadges.map((b) => html`
              <div
                class="condition-badge ${b.isPenalty ? 'penalty' : 'tactical'}"
                @mouseenter=${() => { sheet.activeTooltipCondition = b.name; }}
                @mouseleave=${() => { sheet.activeTooltipCondition = null; }}
                @click=${() => { sheet.activeTooltipCondition = sheet.activeTooltipCondition === b.name ? null : b.name; }}
              >
                <span>${b.details.icon}</span><span>${b.name}</span>
                <button class="remove-condition-btn" title="Dismiss condition" @click=${(e: Event) => { e.stopPropagation(); sheet.handleRemoveCondition(b.id, b.name); }}>✕</button>
                ${sheet.activeTooltipCondition === b.name ? html`
                  <div class="condition-tooltip">
                    <div class="tooltip-title"><span>${b.name.toUpperCase()}</span><span>${b.isPenalty ? 'Absence Penalty' : 'Tactical'}</span></div>
                    <div>${b.details.mechanics}</div>
                    <div class="tooltip-detail"><strong>Saving Throw:</strong> ${b.details.savingThrowModifier}</div>
                  </div>` : html``}
              </div>`)}
      </div>
      <div style="display:flex; gap:6px; margin-top:8px;">
        <select .value=${sheet.selectedConditionToAdd} @change=${(e: any) => { sheet.selectedConditionToAdd = e.target.value; }} style="flex:1; font-size:0.8rem; padding:4px; border:1px solid var(--rf-border-color);">
          <optgroup label="Tactical Conditions">
            <option value="blinded">Blinded</option><option value="prone">Prone</option><option value="stunned">Stunned</option>
            <option value="poisoned">Poisoned</option><option value="frightened">Frightened</option><option value="unconscious">Unconscious</option>
          </optgroup>
          <optgroup label="Runefoble Absence Penalties">
            <option value="drunk">Drunk (Session Miss)</option><option value="foolishness">Foolishness (Session Miss)</option>
            <option value="greed">Greed (Session Miss)</option><option value="cowardice">Cowardice (Session Miss)</option>
          </optgroup>
        </select>
        <button class="action-btn" @click=${() => sheet.handleApplyCondition(sheet.selectedConditionToAdd)}>+ Apply</button>
      </div>
    </div>
  `;
}
