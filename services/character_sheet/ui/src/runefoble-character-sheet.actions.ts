import type { CharacterSheetCondition, EncumbranceInfo, EquipmentSlots, InventoryItem } from './runefoble-character-sheet.types.ts';
import { KNOWN_CONDITION_DETAILS } from './runefoble-character-sheet.types.ts';

export function dispatchActionEvent(target: EventTarget, type: string, detail: unknown): boolean {
  return target.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true }));
}

export function calculateEncumbrance(inventory: InventoryItem[], strength: number): EncumbranceInfo {
  const totalWeight = inventory.reduce((sum, item) => sum + (item.weight_lbs || 0) * (item.quantity || 1), 0);
  const maxCapacity = Math.max(50, strength * 10);
  const lightThreshold = strength * 3.33, mediumThreshold = strength * 6.66, heavyThreshold = maxCapacity;
  let tier: EncumbranceInfo['tier'] = 'light';
  if (totalWeight > heavyThreshold) tier = 'overburdened';
  else if (totalWeight > mediumThreshold) tier = 'heavy';
  else if (totalWeight > lightThreshold) tier = 'medium';
  const percentage = Math.min(100, Math.round((totalWeight / maxCapacity) * 100));
  return { totalWeight, maxCapacity, tier, percentage, lightThreshold, mediumThreshold, heavyThreshold };
}

export function calculateHpDelta(currentHp: number, maxHp: number, delta: number): number {
  return Math.max(0, Math.min(maxHp, currentHp + delta));
}

export function equipItem(equipment: EquipmentSlots, inventory: InventoryItem[], slot: string, item: InventoryItem) {
  const nextEq = { ...equipment, [slot]: item.name };
  const nextInv = inventory.map((inv) => (inv.item_id === item.item_id ? { ...inv, slot: slot as any } : inv));
  return { equipment: nextEq, inventory: nextInv };
}

export function unequipItem(equipment: EquipmentSlots, inventory: InventoryItem[], slot: string) {
  const itemName = equipment[slot];
  if (!itemName) return { equipment, inventory, unequippedName: undefined };
  const nextEq = { ...equipment };
  delete nextEq[slot];
  const nextInv = inventory.map((inv) => (inv.name === itemName ? { ...inv, slot: undefined } : inv));
  return { equipment: nextEq, inventory: nextInv, unequippedName: itemName };
}

export function addItem(inventory: InventoryItem[], name: string, weight = 1.0) {
  const trimmed = name.trim();
  if (!trimmed) return { inventory, addedItem: undefined };
  const item: InventoryItem = { item_id: `item-${Date.now()}`, name: trimmed, quantity: 1, weight_lbs: weight || 1.0 };
  return { inventory: [...inventory, item], addedItem: item };
}

export function removeItem(equipment: EquipmentSlots, inventory: InventoryItem[], item: InventoryItem) {
  let nextEq = equipment;
  let nextInv: InventoryItem[];
  if (item.quantity > 1) {
    nextInv = inventory.map((i) => (i.item_id === item.item_id ? { ...i, quantity: i.quantity - 1 } : i));
  } else {
    nextInv = inventory.filter((i) => i.item_id !== item.item_id);
    for (const [slot, name] of Object.entries(equipment)) {
      if (name === item.name) { nextEq = { ...nextEq }; delete nextEq[slot]; }
    }
  }
  return { equipment: nextEq, inventory: nextInv };
}

export function toggleSpellSlotPip(slots: Record<number, number>, maxSlots: Record<number, number>, tier: number, pipIndex: number) {
  const current = slots[tier] ?? 0;
  const max = maxSlots[tier] ?? current;
  if (pipIndex < current) {
    return { slots: { ...slots, [tier]: current - 1 }, remaining: current - 1, action: 'expend-slot' as const };
  }
  const next = Math.min(max, current + 1);
  return { slots: { ...slots, [tier]: next }, remaining: next, action: 'restore-slot' as const };
}

export function castSpellSlot(slots: Record<number, number>, tier = 1) {
  const remaining = slots[tier] ?? 0;
  const next = remaining > 0 ? remaining - 1 : remaining;
  return { slots: { ...slots, [tier]: next }, remaining: next };
}

export function togglePreparedSpell(preparedSpells: string[], spellName: string) {
  const isPrepared = preparedSpells.includes(spellName);
  return {
    preparedSpells: isPrepared ? preparedSpells.filter((s) => s !== spellName) : [...preparedSpells, spellName],
    isPrepared: !isPrepared,
  };
}

export function applyConditionToState(conditions: CharacterSheetCondition[], name: string) {
  const key = name.toLowerCase();
  const info = KNOWN_CONDITION_DETAILS[key] || {
    mechanics: 'Standard rules condition.', savingThrowModifier: 'None', icon: '✨', isPenalty: false,
  };
  const newCondition: CharacterSheetCondition = {
    id: `cond-${Date.now()}`, name: key, source: info.isPenalty ? 'session_penalty' : 'tactical',
    description: info.mechanics, mechanics: info.mechanics, savingThrowModifier: info.savingThrowModifier,
  };
  return { conditions: [...conditions, newCondition], newCondition };
}

export function removeConditionFromState(conditions: CharacterSheetCondition[], penalties: Record<string, string>, conditionId: string, name: string) {
  const nextConditions = conditions.filter((c) => c.id !== conditionId);
  const key = name.toLowerCase();
  let nextPenalties = penalties;
  if (penalties[key]) { nextPenalties = { ...penalties }; delete nextPenalties[key]; }
  return { conditions: nextConditions, penalties: nextPenalties };
}

export function syncCharacterResponse(host: any, d: any) {
  if (d.name) host.characterName = d.name;
  if (d.character_class) host.characterClass = d.character_class;
  if (d.level != null) host.level = d.level;
  if (d.current_hp != null) host.currentHp = d.current_hp;
  if (d.max_hp != null) host.maxHp = d.max_hp;
  host.isAiStandIn = Boolean(d.is_stand_in_active);
  if (d.equipment) host.equipment = { ...d.equipment };
  if (d.inventory) host.inventory = Object.values(d.inventory);
  if (d.penalties) host.penalties = { ...d.penalties };
  if (d.conditions) {
    host.conditions = Object.entries(d.conditions).map(([k, v]: [string, any]) => ({
      id: k, name: v.condition || k, source: v.source || 'tactical',
      description: v.source || 'Tactical condition', duration_rounds: v.duration_rounds,
    }));
  }
  if (d.spell_slots) { host.spellSlots = { ...d.spell_slots }; host.maxSpellSlots = { ...d.spell_slots }; }
  if (d.prepared_spells) host.preparedSpells = [...d.prepared_spells];
  if (d.spellbook) host.spellbook = [...d.spellbook];
  host.requestUpdate();
}
