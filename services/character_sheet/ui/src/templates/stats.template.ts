import { html } from 'lit';
import type { RunefobleCharacterSheet } from '../runefoble-character-sheet.ts';

export function renderSheetHeader(sheet: RunefobleCharacterSheet) {
  return html`
    <div class="sheet-header">
      <div class="char-identity">
        <h1>${sheet.characterName}</h1>
        <div class="char-meta">
          <span>${sheet.characterClass}</span>
          <span>•</span>
          <span>Level ${sheet.level}</span>
        </div>
      </div>
      ${sheet.isAiStandIn ? html`<span class="badge-stand-in">🤖 AI Stand-In Active</span>` : html``}
    </div>
  `;
}

export function renderVitalsGrid(sheet: RunefobleCharacterSheet) {
  const hpPercent = Math.max(0, Math.min(100, (sheet.currentHp / sheet.maxHp) * 100));
  return html`
    <div class="vitals-grid">
      <div class="vital-card">
        <div class="vital-label">Hit Points</div>
        <div class="vital-val">${sheet.currentHp} / ${sheet.maxHp}</div>
        <div class="hp-bar-outer">
          <div class="hp-bar-inner ${hpPercent < 30 ? 'low' : ''}" style="width: ${hpPercent}%"></div>
        </div>
      </div>
      <div class="vital-card">
        <div class="vital-label">Armor Class</div>
        <div class="vital-val">${sheet.armorClass}</div>
      </div>
      <div class="vital-card">
        <div class="vital-label">Initiative</div>
        <div class="vital-val">+${sheet.initiative}</div>
      </div>
      <div class="vital-card">
        <div class="vital-label">Speed</div>
        <div class="vital-val">${sheet.speed} ft</div>
      </div>
      <div class="vital-card">
        <div class="vital-label">Strength</div>
        <div class="vital-val">${sheet.strength}</div>
      </div>
    </div>
  `;
}
