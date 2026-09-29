import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { characterSheetStyles } from './runefoble-character-sheet.styles.ts';
import {
  renderConditionsPanel, renderEquipmentAndInventory,
  renderSheetHeader, renderSpellbookPanel, renderVitalsGrid,
} from './runefoble-character-sheet.templates.ts';
import type { CharacterSheetCondition, EncumbranceInfo, EquipmentSlots, InventoryItem } from './runefoble-character-sheet.types.ts';
import { DEFAULT_EQUIPMENT, DEFAULT_INVENTORY } from './runefoble-character-sheet.types.ts';
import {
  addItem, applyConditionToState, calculateEncumbrance, calculateHpDelta,
  castSpellSlot, dispatchActionEvent, equipItem, removeConditionFromState,
  removeItem, syncCharacterResponse, togglePreparedSpell, toggleSpellSlotPip, unequipItem,
} from './runefoble-character-sheet.actions.ts';

@customElement('runefoble-character-sheet')
export class RunefobleCharacterSheet extends LitElement {
  static styles = [characterSheetStyles];

  @property({ type: String }) characterId = '';
  @property({ type: String }) apiBaseUrl = '/api/v1/characters';
  @property({ type: String }) characterName = 'Valeros the Bold';
  @property({ type: String }) characterClass = 'Fighter 4 / Wizard 1';
  @property({ type: Number }) level = 5;
  @property({ type: Number }) currentHp = 38;
  @property({ type: Number }) maxHp = 44;
  @property({ type: Number }) armorClass = 18;
  @property({ type: Number }) initiative = 2;
  @property({ type: Number }) speed = 30;
  @property({ type: Number }) strength = 15;
  @property({ type: Boolean }) isAiStandIn = false;
  @property({ type: Object }) equipment: EquipmentSlots = { ...DEFAULT_EQUIPMENT };
  @property({ type: Array }) inventory: InventoryItem[] = [...DEFAULT_INVENTORY];
  @property({ type: Array }) conditions: CharacterSheetCondition[] = [];
  @property({ type: Object }) penalties: Record<string, string> = {};
  @property({ type: Object }) spellSlots: Record<number, number> = { 1: 4, 2: 2 };
  @property({ type: Object }) maxSpellSlots: Record<number, number> = { 1: 4, 2: 2 };
  @property({ type: Array }) preparedSpells: string[] = ['Magic Missile', 'Shield'];
  @property({ type: Array }) spellbook: string[] = ['Magic Missile', 'Shield', 'Detect Magic', 'Misty Step'];

  @state() activeTooltipCondition: string | null = null;
  @state() newItemName = '';
  @state() newItemWeight = 1.0;
  @state() selectedConditionToAdd = 'blinded';
  @state() equippingItem: InventoryItem | null = null;
  @state() selectedEquipSlot = 'main_hand';

  openEquipDialog(item: InventoryItem) { this.equippingItem = item; this.selectedEquipSlot = item.slot || 'main_hand'; }
  closeEquipDialog() { this.equippingItem = null; }
  confirmEquipItem() { if (!this.equippingItem) return; this.handleEquipItem(this.selectedEquipSlot, this.equippingItem); this.equippingItem = null; }

  connectedCallback() {
    super.connectedCallback();
    if (this.characterId && typeof window !== 'undefined' && typeof window.fetch === 'function') { this.fetchCharacter().catch(() => {}); }
  }

  async fetchCharacter(): Promise<void> {
    if (!this.characterId) return;
    try {
      const res = await fetch(`${this.apiBaseUrl}/${this.characterId}`);
      if (res.ok) syncCharacterResponse(this, await res.json());
    } catch {}
  }

  get encumbrance(): EncumbranceInfo {
    return calculateEncumbrance(this.inventory, this.strength);
  }

  handleEquipItem(slot: string, item: InventoryItem) {
    const res = equipItem(this.equipment, this.inventory, slot, item);
    this.equipment = res.equipment; this.inventory = res.inventory;
    dispatchActionEvent(this, 'equip-item', { slot, itemName: item.name, itemId: item.item_id });
  }

  handleUnequipItem(slot: string) {
    const res = unequipItem(this.equipment, this.inventory, slot);
    if (!res.unequippedName) return;
    this.equipment = res.equipment; this.inventory = res.inventory;
    dispatchActionEvent(this, 'unequip-item', { slot, itemName: res.unequippedName });
  }

  handleAddItem() {
    const res = addItem(this.inventory, this.newItemName, Number(this.newItemWeight));
    if (!res.addedItem) return;
    this.inventory = res.inventory; this.newItemName = '';
    dispatchActionEvent(this, 'add-item', { item: res.addedItem });
  }

  handleRemoveItem(item: InventoryItem) {
    const res = removeItem(this.equipment, this.inventory, item);
    this.equipment = res.equipment; this.inventory = res.inventory;
    dispatchActionEvent(this, 'remove-item', { itemId: item.item_id, itemName: item.name });
  }

  handleHpDelta(delta: number) {
    this.currentHp = calculateHpDelta(this.currentHp, this.maxHp, delta);
    dispatchActionEvent(this, 'hp-change', { currentHp: this.currentHp, maxHp: this.maxHp, delta });
  }

  handlePipClick(tier: number, pipIndex: number) {
    const res = toggleSpellSlotPip(this.spellSlots, this.maxSpellSlots, tier, pipIndex);
    this.spellSlots = res.slots;
    dispatchActionEvent(this, res.action, { slotLevel: tier, remaining: res.remaining });
  }

  handleCastSpell(spellName: string, tier = 1) {
    this.spellSlots = castSpellSlot(this.spellSlots, tier).slots;
    dispatchActionEvent(this, 'cast-spell', { spellName, slotLevel: tier });
  }

  handleTogglePrepare(spellName: string) {
    const res = togglePreparedSpell(this.preparedSpells, spellName);
    this.preparedSpells = res.preparedSpells;
    dispatchActionEvent(this, 'prepare-spell', { spellName, prepared: res.isPrepared });
  }

  handleApplyCondition(name: string) {
    const res = applyConditionToState(this.conditions, name);
    this.conditions = res.conditions;
    dispatchActionEvent(this, 'apply-condition', { condition: res.newCondition.name, source: res.newCondition.source });
  }

  handleRemoveCondition(conditionId: string, name: string) {
    const res = removeConditionFromState(this.conditions, this.penalties, conditionId, name);
    this.conditions = res.conditions; this.penalties = res.penalties;
    dispatchActionEvent(this, 'remove-condition', { condition: name });
  }

  render() {
    return html`
      ${renderSheetHeader(this)}
      ${renderVitalsGrid(this)}
      <div class="columns-layout">
        ${renderEquipmentAndInventory(this)}
        <div>${renderConditionsPanel(this)}${renderSpellbookPanel(this)}</div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-character-sheet': RunefobleCharacterSheet;
  }
}
