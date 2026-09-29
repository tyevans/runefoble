/**
 * Character Sub-Resource Mutations Client.
 *
 * Implements sub-resource mutation operations against gateway-api with fallback cache synchronization.
 * TASK-0356: Character Sheet Sub-Resource Mutations & Event-Sourced Persistence Integration.
 */

export interface MutationHost {
  apiBase: string;
  request<T>(path: string, init?: RequestInit): Promise<T | null>;
  getFallbackCharacterDetail(characterId: string): any;
}

export async function mutateCharacterHealth(
  host: MutationHost,
  characterId: string,
  delta: number,
  source = 'damage'
): Promise<any> {
  const data = await host.request<any>(`${host.apiBase}/characters/${characterId}/health`, {
    method: 'POST',
    body: JSON.stringify({ delta, source }),
  });
  const fallback = host.getFallbackCharacterDetail(characterId);
  if (fallback) {
    fallback.current_hp = Math.max(0, Math.min(fallback.max_hp ?? fallback.maxHp ?? 10, (fallback.current_hp ?? fallback.currentHp ?? 10) + delta));
    fallback.currentHp = fallback.current_hp;
    if (delta < 0 && fallback.current_hp <= 0 && (fallback.is_stand_in_active || fallback.isAiStandIn)) {
      fallback.current_hp = 0;
      fallback.currentHp = 0;
      fallback.is_stabilized = true;
      fallback.isStabilized = true;
      fallback.conditions = Array.isArray(fallback.conditions)
        ? [...fallback.conditions.filter((c: any) => (c.name || c.id) !== 'unconscious_stabilized'), { id: 'unconscious_stabilized', name: 'unconscious_stabilized', source: 'permadeath_safeguard' }]
        : { ...fallback.conditions, unconscious_stabilized: { condition: 'unconscious_stabilized', source: 'permadeath_safeguard' } };
    }
  }
  return data || fallback;
}

export async function mutateCharacterEquip(
  host: MutationHost,
  characterId: string,
  slot: string,
  itemName: string
): Promise<any> {
  const data = await host.request<any>(`${host.apiBase}/characters/${characterId}/equipment`, {
    method: 'POST',
    body: JSON.stringify({ slot, item_name: itemName }),
  });
  const fallback = host.getFallbackCharacterDetail(characterId);
  if (fallback) {
    if (!fallback.equipment) fallback.equipment = {};
    const oldItem = fallback.equipment[slot];
    fallback.equipment[slot] = itemName;
    if (Array.isArray(fallback.inventory)) {
      const idx = fallback.inventory.findIndex((i: any) => i.name === itemName);
      if (idx !== -1) {
        if (fallback.inventory[idx].quantity > 1) fallback.inventory[idx].quantity -= 1;
        else fallback.inventory.splice(idx, 1);
      }
      if (oldItem && oldItem !== 'empty' && oldItem !== 'None') {
        const existing = fallback.inventory.find((i: any) => i.name === oldItem);
        if (existing) existing.quantity += 1;
        else fallback.inventory.push({ item_id: `inv-${Date.now()}`, itemId: `inv-${Date.now()}`, name: oldItem, quantity: 1, weight_lbs: 2.0, slot });
      }
    }
  }
  return data || fallback;
}

export async function mutateCharacterUnequip(
  host: MutationHost,
  characterId: string,
  slot: string
): Promise<any> {
  const data = await host.request<any>(`${host.apiBase}/characters/${characterId}/equipment/${slot}`, {
    method: 'DELETE',
  });
  const fallback = host.getFallbackCharacterDetail(characterId);
  if (fallback?.equipment && fallback.equipment[slot]) {
    const unequippedName = fallback.equipment[slot];
    delete fallback.equipment[slot];
    if (unequippedName && unequippedName !== 'empty' && unequippedName !== 'None') {
      if (Array.isArray(fallback.inventory)) {
        const found = fallback.inventory.find((i: any) => i.name === unequippedName);
        if (found) found.quantity += 1;
        else fallback.inventory.push({ item_id: `inv-${Date.now()}`, itemId: `inv-${Date.now()}`, name: unequippedName, quantity: 1, weight_lbs: 2.0, slot });
      }
    }
  }
  return data || fallback;
}

export async function mutateCharacterAddInventory(
  host: MutationHost,
  characterId: string,
  item: any
): Promise<any> {
  const itemId = item.item_id || item.itemId || `inv-${Date.now()}`;
  const name = item.name || 'Unknown Item';
  const quantity = item.quantity || 1;
  const weightLbs = item.weight_lbs ?? item.weightLbs ?? item.weight ?? 1.0;
  const data = await host.request<any>(`${host.apiBase}/characters/${characterId}/inventory`, {
    method: 'POST',
    body: JSON.stringify({ item_id: itemId, name, quantity, weight_lbs: weightLbs, slot: item.slot }),
  });
  const fallback = host.getFallbackCharacterDetail(characterId);
  if (fallback) {
    if (Array.isArray(fallback.inventory)) {
      const found = fallback.inventory.find((i: any) => i.item_id === itemId || i.itemId === itemId);
      if (found) found.quantity += quantity;
      else fallback.inventory.push({ item_id: itemId, itemId, name, quantity, weight_lbs: weightLbs, slot: item.slot });
    } else {
      if (!fallback.inventory) fallback.inventory = {};
      if (fallback.inventory[itemId]) fallback.inventory[itemId].quantity += quantity;
      else fallback.inventory[itemId] = { item_id: itemId, itemId, name, quantity, weight_lbs: weightLbs, slot: item.slot };
    }
  }
  return data || fallback;
}

export async function mutateCharacterRemoveInventory(
  host: MutationHost,
  characterId: string,
  itemId: string,
  quantity = 1
): Promise<any> {
  const data = await host.request<any>(`${host.apiBase}/characters/${characterId}/inventory/${itemId}?quantity=${quantity}`, {
    method: 'DELETE',
  });
  const fallback = host.getFallbackCharacterDetail(characterId);
  if (fallback) {
    if (Array.isArray(fallback.inventory)) {
      const idx = fallback.inventory.findIndex((i: any) => i.item_id === itemId || i.itemId === itemId);
      if (idx !== -1) {
        if (fallback.inventory[idx].quantity <= quantity) fallback.inventory.splice(idx, 1);
        else fallback.inventory[idx].quantity -= quantity;
      }
    } else if (fallback.inventory && fallback.inventory[itemId]) {
      if (fallback.inventory[itemId].quantity <= quantity) delete fallback.inventory[itemId];
      else fallback.inventory[itemId].quantity -= quantity;
    }
  }
  return data || fallback;
}

export async function mutateCharacterApplyCondition(
  host: MutationHost,
  characterId: string,
  condition: string,
  source = 'tactical'
): Promise<any> {
  const data = await host.request<any>(`${host.apiBase}/characters/${characterId}/conditions`, {
    method: 'POST',
    body: JSON.stringify({ condition, source }),
  });
  const fallback = host.getFallbackCharacterDetail(characterId);
  if (fallback) {
    const key = condition.toLowerCase();
    if (Array.isArray(fallback.conditions)) {
      if (!fallback.conditions.some((c: any) => (c.name || c.condition || c.id) === key)) {
        fallback.conditions.push({ id: key, name: key, source, description: `Tactical ${condition}` });
      }
    } else {
      if (!fallback.conditions) fallback.conditions = {};
      fallback.conditions[key] = { condition: key, source };
    }
  }
  return data || fallback;
}

export async function mutateCharacterRemoveCondition(
  host: MutationHost,
  characterId: string,
  condition: string
): Promise<any> {
  const data = await host.request<any>(`${host.apiBase}/characters/${characterId}/conditions/${condition}`, {
    method: 'DELETE',
  });
  const fallback = host.getFallbackCharacterDetail(characterId);
  if (fallback) {
    const key = condition.toLowerCase();
    if (Array.isArray(fallback.conditions)) {
      fallback.conditions = fallback.conditions.filter((c: any) => (c.name || c.condition || c.id)?.toLowerCase() !== key);
    } else if (fallback.conditions) {
      delete fallback.conditions[key];
    }
  }
  return data || fallback;
}

export async function mutateCharacterCastSpell(
  host: MutationHost,
  characterId: string,
  spellName: string,
  slotLevel = 1
): Promise<any> {
  const data = await host.request<any>(`${host.apiBase}/characters/${characterId}/spells/cast`, {
    method: 'POST',
    body: JSON.stringify({ spell_name: spellName, slot_level: slotLevel }),
  });
  const fallback = host.getFallbackCharacterDetail(characterId);
  if (fallback) {
    const slots = fallback.spell_slots || fallback.spellSlots;
    if (slots && (slots[slotLevel] ?? 0) > 0) slots[slotLevel] -= 1;
  }
  return data || fallback;
}

export async function mutateCharacterPrepareSpell(
  host: MutationHost,
  characterId: string,
  spellName: string,
  isPrepared = true
): Promise<any> {
  const data = await host.request<any>(`${host.apiBase}/characters/${characterId}/spells/prepare`, {
    method: 'POST',
    body: JSON.stringify({ spell_name: spellName, is_prepared: isPrepared }),
  });
  const fallback = host.getFallbackCharacterDetail(characterId);
  if (fallback) {
    const list = fallback.prepared_spells || fallback.preparedSpells || [];
    if (isPrepared) {
      if (!list.includes(spellName)) list.push(spellName);
    } else {
      const idx = list.indexOf(spellName);
      if (idx !== -1) list.splice(idx, 1);
    }
    fallback.prepared_spells = list;
    fallback.preparedSpells = list;
  }
  return data || fallback;
}

export async function mutateCharacterRestoreSlot(
  host: MutationHost,
  characterId: string,
  slotLevel: number
): Promise<any> {
  const fallback = host.getFallbackCharacterDetail(characterId);
  if (fallback) {
    const slots = fallback.spell_slots || fallback.spellSlots;
    const maxSlots = fallback.max_spell_slots || fallback.maxSpellSlots || slots;
    if (slots && maxSlots && (slots[slotLevel] ?? 0) < (maxSlots[slotLevel] ?? 0)) {
      slots[slotLevel] = (slots[slotLevel] ?? 0) + 1;
    }
  }
  return fallback;
}
