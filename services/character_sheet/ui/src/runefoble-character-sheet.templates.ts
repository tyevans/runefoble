import { html } from 'lit';
import type { RunefobleCharacterSheet } from './runefoble-character-sheet.ts';
import { KNOWN_CONDITION_DETAILS } from './runefoble-character-sheet.types.ts';

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

export function renderEquipmentAndInventory(sheet: RunefobleCharacterSheet) {
  const enc = sheet.encumbrance;
  return html`
    <div class="section-panel">
      <div class="section-title">
        <span>⚔️ Equipment & Inventory</span>
        <span style="font-size:0.75rem; color:var(--rf-text-muted);">${sheet.inventory.length} Items</span>
      </div>

      <!-- Paper Doll Slots -->
      <div class="paper-doll-slots">
        <div class="equip-slot ${sheet.equipment.main_hand ? 'filled' : ''}">
          <div class="slot-label"><span>Main Hand</span><span>⚔️</span></div>
          <div class="slot-content">
            <span>${sheet.equipment.main_hand || 'Empty'}</span>
            ${sheet.equipment.main_hand
              ? html`<button class="unequip-btn" title="Unequip" @click=${() => sheet.handleUnequipItem('main_hand')}>✕</button>`
              : html``}
          </div>
        </div>

        <div class="equip-slot ${sheet.equipment.off_hand ? 'filled' : ''}">
          <div class="slot-label"><span>Off Hand</span><span>🛡️</span></div>
          <div class="slot-content">
            <span>${sheet.equipment.off_hand || 'Empty'}</span>
            ${sheet.equipment.off_hand
              ? html`<button class="unequip-btn" title="Unequip" @click=${() => sheet.handleUnequipItem('off_hand')}>✕</button>`
              : html``}
          </div>
        </div>

        <div class="equip-slot ${sheet.equipment.armor ? 'filled' : ''}">
          <div class="slot-label"><span>Armor</span><span>🥋</span></div>
          <div class="slot-content">
            <span>${sheet.equipment.armor || 'Unarmored'}</span>
            ${sheet.equipment.armor
              ? html`<button class="unequip-btn" title="Unequip" @click=${() => sheet.handleUnequipItem('armor')}>✕</button>`
              : html``}
          </div>
        </div>

        <div class="equip-slot ${sheet.equipment.accessory ? 'filled' : ''}">
          <div class="slot-label"><span>Accessory</span><span>💍</span></div>
          <div class="slot-content">
            <span>${sheet.equipment.accessory || 'Empty'}</span>
            ${sheet.equipment.accessory
              ? html`<button class="unequip-btn" title="Unequip" @click=${() => sheet.handleUnequipItem('accessory')}>✕</button>`
              : html``}
          </div>
        </div>
      </div>

      <!-- Encumbrance Capacity Bar -->
      <div class="encumbrance-box">
        <div class="encumbrance-header">
          <span>Encumbrance (${enc.tier.toUpperCase()})</span>
          <span>${enc.totalWeight.toFixed(1)} / ${enc.maxCapacity} lbs</span>
        </div>
        <div class="encumbrance-bar-bg" title="Capacity: ${enc.totalWeight} lbs / ${enc.maxCapacity} lbs">
          <div class="encumbrance-bar-fill tier-${enc.tier}" style="width: ${enc.percentage}%"></div>
        </div>
      </div>

      <!-- Inventory Table -->
      <table class="inventory-table">
        <thead>
          <tr>
            <th>Item</th>
            <th>Qty</th>
            <th>Wt (lbs)</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${sheet.inventory.map(
            (item) => html`
              <tr class="inventory-row">
                <td>
                  <strong>${item.name}</strong>
                  ${item.slot ? html`<span style="font-size:0.68rem; color:var(--rf-accent-secondary); margin-left:4px;">[${item.slot}]</span>` : html``}
                </td>
                <td>x${item.quantity}</td>
                <td>${(item.weight_lbs * item.quantity).toFixed(1)}</td>
                <td>
                  <button class="action-btn" title="Equip into slot" @click=${() => sheet.handleEquipItem(item.slot || 'main_hand', item)}>Equip</button>
                  <button class="action-btn" title="Drop item" @click=${() => sheet.handleRemoveItem(item)}>Drop</button>
                </td>
              </tr>
            `
          )}
        </tbody>
      </table>

      <!-- Add Item Row -->
      <div style="display:flex; gap:6px; margin-top:12px;">
        <input
          type="text"
          placeholder="New Item Name"
          .value=${sheet.newItemName}
          @input=${(e: any) => { sheet.newItemName = e.target.value; }}
          style="flex:2; font-size:0.8rem; padding:4px; border:1px solid var(--rf-border-color);"
        />
        <input
          type="number"
          placeholder="lbs"
          .value=${String(sheet.newItemWeight)}
          @input=${(e: any) => { sheet.newItemWeight = Number(e.target.value); }}
          style="width:55px; font-size:0.8rem; padding:4px; border:1px solid var(--rf-border-color);"
        />
        <button class="action-btn" @click=${() => sheet.handleAddItem()}>+ Add</button>
      </div>
    </div>
  `;
}

export function renderConditionsPanel(sheet: RunefobleCharacterSheet) {
  const allBadges: { id: string; name: string; isPenalty: boolean; details: any }[] = [];
  sheet.conditions.forEach((c) => {
    const key = c.name.toLowerCase();
    const details = KNOWN_CONDITION_DETAILS[key] || {
      mechanics: c.description || 'Active condition.',
      savingThrowModifier: 'Standard',
      icon: c.source === 'session_penalty' ? '🍺' : '⚔️',
      isPenalty: c.source === 'session_penalty',
    };
    allBadges.push({ id: c.id, name: c.name, isPenalty: details.isPenalty || false, details });
  });
  Object.entries(sheet.penalties).forEach(([k, desc]) => {
    if (!allBadges.some((b) => b.name.toLowerCase() === k.toLowerCase())) {
      const details = KNOWN_CONDITION_DETAILS[k.toLowerCase()] || {
        mechanics: desc,
        savingThrowModifier: 'Modified by DM',
        icon: '🍺',
        isPenalty: true,
      };
      allBadges.push({ id: `pen-${k}`, name: k, isPenalty: true, details });
    }
  });

  return html`
    <div class="section-panel" style="margin-bottom:18px;">
      <div class="section-title">
        <span>⚡ Conditions & Penalties</span>
        <span style="font-size:0.75rem; color:var(--rf-text-muted);">${allBadges.length} Active</span>
      </div>

      <div class="conditions-grid">
        ${allBadges.length === 0
          ? html`<div style="font-size:0.8rem; color:var(--rf-text-muted); font-style:italic;">No active conditions or penalties.</div>`
          : allBadges.map(
              (b) => html`
                <div
                  class="condition-badge ${b.isPenalty ? 'penalty' : 'tactical'}"
                  @mouseenter=${() => { sheet.activeTooltipCondition = b.name; }}
                  @mouseleave=${() => { sheet.activeTooltipCondition = null; }}
                  @click=${() => { sheet.activeTooltipCondition = sheet.activeTooltipCondition === b.name ? null : b.name; }}
                >
                  <span>${b.details.icon}</span>
                  <span>${b.name}</span>
                  <button
                    class="remove-condition-btn"
                    title="Dismiss condition"
                    @click=${(e: Event) => {
                      e.stopPropagation();
                      sheet.handleRemoveCondition(b.id, b.name);
                    }}
                  >
                    ✕
                  </button>

                  ${sheet.activeTooltipCondition === b.name
                    ? html`
                        <div class="condition-tooltip">
                          <div class="tooltip-title">
                            <span>${b.name.toUpperCase()}</span>
                            <span>${b.isPenalty ? 'Absence Penalty' : 'Tactical'}</span>
                          </div>
                          <div>${b.details.mechanics}</div>
                          <div class="tooltip-detail">
                            <strong>Saving Throw:</strong> ${b.details.savingThrowModifier}
                          </div>
                        </div>
                      `
                    : html``}
                </div>
              `
            )}
      </div>

      <!-- Apply Condition Selector -->
      <div style="display:flex; gap:6px; margin-top:8px;">
        <select
          .value=${sheet.selectedConditionToAdd}
          @change=${(e: any) => { sheet.selectedConditionToAdd = e.target.value; }}
          style="flex:1; font-size:0.8rem; padding:4px; border:1px solid var(--rf-border-color);"
        >
          <optgroup label="Tactical Conditions">
            <option value="blinded">Blinded</option>
            <option value="prone">Prone</option>
            <option value="stunned">Stunned</option>
            <option value="poisoned">Poisoned</option>
            <option value="frightened">Frightened</option>
            <option value="unconscious">Unconscious</option>
          </optgroup>
          <optgroup label="Runefoble Absence Penalties">
            <option value="drunk">Drunk (Session Miss)</option>
            <option value="foolishness">Foolishness (Session Miss)</option>
            <option value="greed">Greed (Session Miss)</option>
            <option value="cowardice">Cowardice (Session Miss)</option>
          </optgroup>
        </select>
        <button class="action-btn" @click=${() => sheet.handleApplyCondition(sheet.selectedConditionToAdd)}>+ Apply</button>
      </div>
    </div>
  `;
}

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
                    >
                      ${isAvailable ? '●' : '○'}
                    </button>
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
          : sheet.preparedSpells.map(
              (spell) => html`
                <li class="spell-item">
                  <span>${spell}</span>
                  <div class="spell-tags">
                    <span class="spell-badge-prepared">Prepared</span>
                    <button class="action-btn" @click=${() => sheet.handleCastSpell(spell, 1)}>Cast</button>
                  </div>
                </li>
              `
            )}
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
