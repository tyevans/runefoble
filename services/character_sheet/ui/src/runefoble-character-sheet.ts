import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { characterSheetStyles } from './runefoble-character-sheet.styles.ts';
import {
  renderConditionsPanel,
  renderEquipmentAndInventory,
  renderSheetHeader,
  renderSpellbookPanel,
  renderVitalsGrid,
} from './runefoble-character-sheet.templates.ts';
import {
  KNOWN_CONDITION_DETAILS,
} from './runefoble-character-sheet.types.ts';
import type {
  CharacterSheetCondition,
  EncumbranceInfo,
  EquipmentSlots,
  InventoryItem,
} from './runefoble-character-sheet.types.ts';

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

  @property({ type: Object }) equipment: EquipmentSlots = {
    main_hand: 'Longsword +1',
    off_hand: 'Steel Shield',
    armor: 'Chain Mail',
    accessory: 'Ring of Protection',
  };

  @property({ type: Array }) inventory: InventoryItem[] = [
    { item_id: 'i-1', name: 'Longsword +1', quantity: 1, weight_lbs: 3.0, slot: 'main_hand' },
    { item_id: 'i-2', name: 'Steel Shield', quantity: 1, weight_lbs: 6.0, slot: 'off_hand' },
    { item_id: 'i-3', name: 'Chain Mail', quantity: 1, weight_lbs: 55.0, slot: 'armor' },
    { item_id: 'i-4', name: 'Ring of Protection', quantity: 1, weight_lbs: 0.1, slot: 'accessory' },
    { item_id: 'i-5', name: 'Healing Potion', quantity: 3, weight_lbs: 0.5 },
    { item_id: 'i-6', name: 'Rations (5 days)', quantity: 5, weight_lbs: 2.0 },
    { item_id: 'i-7', name: 'Dungeoneer Pack', quantity: 1, weight_lbs: 12.0 },
  ];

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

  connectedCallback() {
    super.connectedCallback();
    if (this.characterId && typeof window !== 'undefined' && typeof window.fetch === 'function') {
      this.fetchCharacter().catch(() => {});
    }
  }

  async fetchCharacter(): Promise<void> {
    if (!this.characterId) return;
    try {
      const res = await fetch(`${this.apiBaseUrl}/${this.characterId}`);
      if (!res.ok) return;
      const data = await res.json();
      this.characterName = data.name || this.characterName;
      this.characterClass = data.character_class || this.characterClass;
      this.level = data.level ?? this.level;
      this.currentHp = data.current_hp ?? this.currentHp;
      this.maxHp = data.max_hp ?? this.maxHp;
      this.isAiStandIn = Boolean(data.is_stand_in_active);
      if (data.equipment) this.equipment = { ...data.equipment };
      if (data.inventory) {
        this.inventory = Object.values(data.inventory);
      }
      if (data.penalties) this.penalties = { ...data.penalties };
      if (data.conditions) {
        this.conditions = Object.entries(data.conditions).map(([k, v]: [string, any]) => ({
          id: k,
          name: v.condition || k,
          source: v.source || 'tactical',
          description: v.source || 'Tactical condition',
          duration_rounds: v.duration_rounds,
        }));
      }
      if (data.spell_slots) {
        this.spellSlots = { ...data.spell_slots };
        this.maxSpellSlots = { ...data.spell_slots };
      }
      if (data.prepared_spells) this.preparedSpells = [...data.prepared_spells];
      if (data.spellbook) this.spellbook = [...data.spellbook];
      this.requestUpdate();
    } catch {
      // Graceful fallback to initial properties
    }
  }

  get encumbrance(): EncumbranceInfo {
    const totalWeight = this.inventory.reduce((sum, item) => sum + (item.weight_lbs || 0) * (item.quantity || 1), 0);
    const maxCapacity = Math.max(50, this.strength * 10);
    const lightThreshold = this.strength * 3.33;
    const mediumThreshold = this.strength * 6.66;
    const heavyThreshold = maxCapacity;

    let tier: EncumbranceInfo['tier'] = 'light';
    if (totalWeight > heavyThreshold) tier = 'overburdened';
    else if (totalWeight > mediumThreshold) tier = 'heavy';
    else if (totalWeight > lightThreshold) tier = 'medium';

    const percentage = Math.min(100, Math.round((totalWeight / maxCapacity) * 100));
    return { totalWeight, maxCapacity, tier, percentage, lightThreshold, mediumThreshold, heavyThreshold };
  }

  handleEquipItem(slot: string, item: InventoryItem) {
    this.equipment = { ...this.equipment, [slot]: item.name };
    this.inventory = this.inventory.map((inv) =>
      inv.item_id === item.item_id ? { ...inv, slot: slot as any } : inv
    );
    this.dispatchEvent(
      new CustomEvent('equip-item', {
        detail: { slot, itemName: item.name, itemId: item.item_id },
        bubbles: true,
        composed: true,
      })
    );
  }

  handleUnequipItem(slot: string) {
    const itemName = this.equipment[slot];
    if (!itemName) return;
    const updated = { ...this.equipment };
    delete updated[slot];
    this.equipment = updated;
    this.inventory = this.inventory.map((inv) =>
      inv.name === itemName ? { ...inv, slot: undefined } : inv
    );
    this.dispatchEvent(
      new CustomEvent('unequip-item', {
        detail: { slot, itemName },
        bubbles: true,
        composed: true,
      })
    );
  }

  handleAddItem() {
    if (!this.newItemName.trim()) return;
    const newItem: InventoryItem = {
      item_id: `item-${Date.now()}`,
      name: this.newItemName.trim(),
      quantity: 1,
      weight_lbs: Number(this.newItemWeight) || 1.0,
    };
    this.inventory = [...this.inventory, newItem];
    this.newItemName = '';
    this.dispatchEvent(
      new CustomEvent('add-item', {
        detail: { item: newItem },
        bubbles: true,
        composed: true,
      })
    );
  }

  handleRemoveItem(item: InventoryItem) {
    if (item.quantity > 1) {
      this.inventory = this.inventory.map((i) =>
        i.item_id === item.item_id ? { ...i, quantity: i.quantity - 1 } : i
      );
    } else {
      this.inventory = this.inventory.filter((i) => i.item_id !== item.item_id);
      for (const [slot, name] of Object.entries(this.equipment)) {
        if (name === item.name) {
          this.handleUnequipItem(slot);
        }
      }
    }
    this.dispatchEvent(
      new CustomEvent('remove-item', {
        detail: { itemId: item.item_id, itemName: item.name },
        bubbles: true,
        composed: true,
      })
    );
  }

  handlePipClick(tier: number, pipIndex: number) {
    const currentRemaining = this.spellSlots[tier] ?? 0;
    const max = this.maxSpellSlots[tier] ?? currentRemaining;
    if (pipIndex < currentRemaining) {
      const newRemaining = currentRemaining - 1;
      this.spellSlots = { ...this.spellSlots, [tier]: newRemaining };
      this.dispatchEvent(
        new CustomEvent('expend-slot', {
          detail: { slotLevel: tier, remaining: newRemaining },
          bubbles: true,
          composed: true,
        })
      );
    } else {
      const newRemaining = Math.min(max, currentRemaining + 1);
      this.spellSlots = { ...this.spellSlots, [tier]: newRemaining };
      this.dispatchEvent(
        new CustomEvent('restore-slot', {
          detail: { slotLevel: tier, remaining: newRemaining },
          bubbles: true,
          composed: true,
        })
      );
    }
  }

  handleCastSpell(spellName: string, tier = 1) {
    const remaining = this.spellSlots[tier] ?? 0;
    if (remaining > 0) {
      this.spellSlots = { ...this.spellSlots, [tier]: remaining - 1 };
    }
    this.dispatchEvent(
      new CustomEvent('cast-spell', {
        detail: { spellName, slotLevel: tier },
        bubbles: true,
        composed: true,
      })
    );
  }

  handleTogglePrepare(spellName: string) {
    const isPrepared = this.preparedSpells.includes(spellName);
    if (isPrepared) {
      this.preparedSpells = this.preparedSpells.filter((s) => s !== spellName);
    } else {
      this.preparedSpells = [...this.preparedSpells, spellName];
    }
    this.dispatchEvent(
      new CustomEvent('prepare-spell', {
        detail: { spellName, prepared: !isPrepared },
        bubbles: true,
        composed: true,
      })
    );
  }

  handleApplyCondition(name: string) {
    const key = name.toLowerCase();
    const info = KNOWN_CONDITION_DETAILS[key] || {
      mechanics: 'Standard rules condition.',
      savingThrowModifier: 'None',
      icon: '✨',
      isPenalty: false,
    };
    const newCond: CharacterSheetCondition = {
      id: `cond-${Date.now()}`,
      name: key,
      source: info.isPenalty ? 'session_penalty' : 'tactical',
      description: info.mechanics,
      mechanics: info.mechanics,
      savingThrowModifier: info.savingThrowModifier,
    };
    this.conditions = [...this.conditions, newCond];
    this.dispatchEvent(
      new CustomEvent('apply-condition', {
        detail: { condition: key, source: newCond.source },
        bubbles: true,
        composed: true,
      })
    );
  }

  handleRemoveCondition(conditionId: string, name: string) {
    this.conditions = this.conditions.filter((c) => c.id !== conditionId);
    if (this.penalties[name.toLowerCase()]) {
      const updated = { ...this.penalties };
      delete updated[name.toLowerCase()];
      this.penalties = updated;
    }
    this.dispatchEvent(
      new CustomEvent('remove-condition', {
        detail: { condition: name },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    return html`
      ${renderSheetHeader(this)}
      ${renderVitalsGrid(this)}
      <div class="columns-layout">
        ${renderEquipmentAndInventory(this)}
        <div>
          ${renderConditionsPanel(this)}
          ${renderSpellbookPanel(this)}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-character-sheet': RunefobleCharacterSheet;
  }
}
