import { html } from 'lit';
import type { RunefobleCharacterSheet } from '../runefoble-character-sheet.ts';
import type { InventoryItem } from '../runefoble-character-sheet.types.ts';

interface EquipmentSlotConfig {
  key: 'main_hand' | 'off_hand' | 'armor' | 'accessory';
  label: string;
  icon: string;
  emptyLabel: string;
}

const EQUIPMENT_SLOTS: EquipmentSlotConfig[] = [
  { key: 'main_hand', label: 'Main Hand', icon: '⚔️', emptyLabel: 'Empty' },
  { key: 'off_hand', label: 'Off Hand', icon: '🛡️', emptyLabel: 'Empty' },
  { key: 'armor', label: 'Armor', icon: '🥋', emptyLabel: 'Unarmored' },
  { key: 'accessory', label: 'Accessory', icon: '💍', emptyLabel: 'Empty' },
];

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
        ${EQUIPMENT_SLOTS.map((slot) => {
          const item = sheet.equipment[slot.key];
          return html`
            <div class="equip-slot ${item ? 'filled' : ''}">
              <div class="slot-label"><span>${slot.label}</span><span>${slot.icon}</span></div>
              <div class="slot-content">
                <span>${item || slot.emptyLabel}</span>
                ${item ? html`<button class="unequip-btn" title="Unequip" @click=${() => sheet.handleUnequipItem(slot.key)}>✕</button>` : html``}
              </div>
            </div>
          `;
        })}
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
            <th>Item</th><th>Qty</th><th>Wt (lbs)</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${sheet.inventory.map(
            (item: InventoryItem) => html`
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
          type="text" placeholder="New Item Name" .value=${sheet.newItemName}
          @input=${(e: any) => { sheet.newItemName = e.target.value; }}
          style="flex:2; font-size:0.8rem; padding:4px; border:1px solid var(--rf-border-color);"
        />
        <input
          type="number" placeholder="lbs" .value=${String(sheet.newItemWeight)}
          @input=${(e: any) => { sheet.newItemWeight = Number(e.target.value); }}
          style="width:55px; font-size:0.8rem; padding:4px; border:1px solid var(--rf-border-color);"
        />
        <button class="action-btn" @click=${() => sheet.handleAddItem()}>+ Add</button>
      </div>
    </div>
  `;
}
