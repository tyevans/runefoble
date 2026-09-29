import { html } from 'lit';
import type { RunefobleCharacterSheet } from '../runefoble-character-sheet.ts';

export const KNOWN_SPELL_LEVELS: Record<string, number> = {
  'shield': 1,
  'magic missile': 1,
  'detect magic': 1,
  'cure wounds': 1,
  'healing word': 1,
  'misty step': 2,
  'hold person': 2,
  'fireball': 3,
  'counterspell': 3,
  'lightning bolt': 3,
};

export function renderSpellbookPanel(sheet: RunefobleCharacterSheet) {
  return html`
    <div class="section-panel">
      <div class="section-title">
        <span>✨ Spellbook & Slot Tracker</span>
        <span style="font-size:0.75rem; color:var(--rf-text-muted);">${sheet.preparedSpells.length} Prepared</span>
      </div>

      <!-- Spell Slots by Tier with Clickable Pips -->
      <div style="margin-bottom:12px;">
        ${Object.entries(sheet.maxSpellSlots).map(([tierStr, maxCount]) => {
          const tier = Number(tierStr);
          const remaining = sheet.spellSlots[tier] ?? 0;
          return html`
            <div class="spell-tier-row">
              <span class="tier-label">Tier ${tier}</span>
              <div class="pips-container">
                ${Array.from({ length: maxCount }).map((_, idx) => {
                  const isAvailable = idx < remaining;
                  return html`
                    <button
                      class="spell-pip ${isAvailable ? '' : 'expended'}"
                      title="${isAvailable ? `Tier ${tier} Slot ${idx + 1}: Available (Click to expend)` : `Tier ${tier} Slot ${idx + 1}: Expended (Click to recover)`}"
                      @click=${() => sheet.handlePipClick(tier, idx)}
                    >${isAvailable ? '●' : '○'}</button>
                  `;
                })}
              </div>
            </div>
          `;
        })}
      </div>

      <!-- Prepared Spells -->
      <div style="font-size:0.75rem; font-weight:800; text-transform:uppercase; color:var(--rf-text-muted); margin-bottom:4px;">
        Prepared Spells
      </div>
      <ul class="spell-list">
        ${sheet.preparedSpells.length === 0
          ? html`<li style="font-size:0.8rem; color:var(--rf-text-muted); font-style:italic;">No spells prepared.</li>`
          : sheet.preparedSpells.map((spell: any) => {
              const spellName = typeof spell === 'string' ? spell : spell?.name || '';
              const spellLevel = (typeof spell === 'object' && spell !== null && 'level' in spell)
                ? spell.level
                : (KNOWN_SPELL_LEVELS[spellName.toLowerCase().trim()] ?? 1);
              return html`
                <li class="spell-item">
                  <span>${spellName} <small style="color:var(--rf-text-muted);">(Tier ${spellLevel})</small></span>
                  <div class="spell-tags">
                    <span class="spell-badge-prepared">Prepared</span>
                    <button class="action-btn cast-spell-btn" @click=${() => sheet.handleCastSpell(spellName, (spell as any)?.level ?? spellLevel)}>Cast</button>
                  </div>
                </li>
              `;
            })}
      </ul>

      <!-- All Known Spells in Spellbook -->
      <div style="font-size:0.75rem; font-weight:800; text-transform:uppercase; color:var(--rf-text-muted); margin-top:12px; margin-bottom:4px;">
        Known Spellbook
      </div>
      <ul class="spell-list">
        ${sheet.spellbook.map((spell) => {
          const isPrep = sheet.preparedSpells.includes(spell);
          return html`
            <li class="spell-item">
              <span>${spell}</span>
              <button class="action-btn" @click=${() => sheet.handleTogglePrepare(spell)}>
                ${isPrep ? 'Unprepare' : 'Prepare'}
              </button>
            </li>
          `;
        })}
      </ul>
    </div>
  `;
}
