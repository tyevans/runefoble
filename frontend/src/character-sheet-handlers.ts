/**
 * Character Sheet Action Event Handlers.
 *
 * Dispatches character sub-resource mutations from <runefoble-character-sheet>
 * to appDataService with optimistic UI updates and toast notifications.
 * TASK-0356: Character Sheet Sub-Resource Mutations & Event-Sourced Persistence Integration.
 */

import { appDataService } from './services/app-data-service.ts';

export interface SheetAppHost {
  selectedCharacter: any;
  characters: any[];
  activeCharacter: any;
  showToast(message: string): void;
}

export async function handleSheetHpChange(host: any, charId: string, e: CustomEvent) {
  const { delta, currentHp, maxHp } = e.detail || {};
  await appDataService.modifyCharacterHealth(charId, delta);
  if (host.selectedCharacter) { host.selectedCharacter.currentHp = currentHp; host.selectedCharacter.current_hp = currentHp; }
  host.characters = host.characters.map((c: any) => (c.id === charId ? { ...c, currentHp } : c));
  if (host.activeCharacter?.id === charId) host.activeCharacter = { ...host.activeCharacter, currentHp };
  host.showToast(delta >= 0 ? `Healed ${delta} HP (${currentHp}/${maxHp})` : `Took ${Math.abs(delta)} damage (${currentHp}/${maxHp})`);
}

export async function handleSheetEquipItem(host: any, charId: string, e: CustomEvent) {
  const { slot, itemName } = e.detail || {};
  await appDataService.equipCharacterItem(charId, slot, itemName);
  if (host.selectedCharacter) { if (!host.selectedCharacter.equipment) host.selectedCharacter.equipment = {}; host.selectedCharacter.equipment[slot] = itemName; }
  host.showToast(`Equipped ${itemName} to ${slot.replace('_', ' ')}`);
}

export async function handleSheetUnequipItem(host: any, charId: string, e: CustomEvent) {
  const { slot, itemName } = e.detail || {};
  await appDataService.unequipCharacterItem(charId, slot);
  if (host.selectedCharacter?.equipment) delete host.selectedCharacter.equipment[slot];
  host.showToast(`Unequipped ${itemName || slot.replace('_', ' ')}`);
}

export async function handleSheetAddItem(host: any, charId: string, e: CustomEvent) {
  const { item } = e.detail || {};
  if (!item) return;
  await appDataService.addCharacterInventoryItem(charId, item);
  if (host.selectedCharacter) {
    const inv = Array.isArray(host.selectedCharacter.inventory) ? host.selectedCharacter.inventory : Object.values(host.selectedCharacter.inventory || {});
    host.selectedCharacter.inventory = [...inv, item];
  }
  host.showToast(`Added ${item.name} to inventory`);
}

export async function handleSheetRemoveItem(host: any, charId: string, e: CustomEvent) {
  const { itemId, itemName } = e.detail || {};
  await appDataService.removeCharacterInventoryItem(charId, itemId);
  if (host.selectedCharacter && Array.isArray(host.selectedCharacter.inventory)) {
    host.selectedCharacter.inventory = host.selectedCharacter.inventory.filter((i: any) => i.item_id !== itemId && i.itemId !== itemId);
  }
  host.showToast(`Removed ${itemName || 'item'} from inventory`);
}

export async function handleSheetCastSpell(host: any, charId: string, e: CustomEvent) {
  const { spellName, slotLevel } = e.detail || {};
  await appDataService.castCharacterSpell(charId, spellName, slotLevel);
  if (host.selectedCharacter) {
    const s = host.selectedCharacter.spellSlots || host.selectedCharacter.spell_slots;
    if (s && s[slotLevel] > 0) s[slotLevel] -= 1;
  }
  host.showToast(`Cast ${spellName} (Tier ${slotLevel})`);
}

export async function handleSheetPrepareSpell(host: any, charId: string, e: CustomEvent) {
  const { spellName, prepared } = e.detail || {};
  await appDataService.prepareCharacterSpell(charId, spellName, prepared);
  if (host.selectedCharacter) {
    const list = host.selectedCharacter.preparedSpells || host.selectedCharacter.prepared_spells || [];
    if (prepared && !list.includes(spellName)) list.push(spellName);
    else if (!prepared) { const idx = list.indexOf(spellName); if (idx !== -1) list.splice(idx, 1); }
    host.selectedCharacter.preparedSpells = list;
  }
  host.showToast(prepared ? `Prepared ${spellName}` : `Unprepared ${spellName}`);
}

export async function handleSheetApplyCondition(host: any, charId: string, e: CustomEvent) {
  const { condition, source } = e.detail || {};
  await appDataService.applyCharacterCondition(charId, condition, source);
  if (host.selectedCharacter && Array.isArray(host.selectedCharacter.conditions)) {
    host.selectedCharacter.conditions.push({ id: condition, name: condition, source: source || 'tactical' });
  }
  host.showToast(`Condition ${condition} applied`);
}

export async function handleSheetRemoveCondition(host: any, charId: string, e: CustomEvent) {
  const { condition } = e.detail || {};
  await appDataService.removeCharacterCondition(charId, condition);
  if (host.selectedCharacter && Array.isArray(host.selectedCharacter.conditions)) {
    host.selectedCharacter.conditions = host.selectedCharacter.conditions.filter((c: any) => (c.name || c.id) !== condition);
  }
  host.showToast(`Condition ${condition} removed`);
}

export async function handleSheetExpendSlot(host: any, charId: string, e: CustomEvent) {
  const { slotLevel, remaining } = e.detail || {};
  await appDataService.castCharacterSpell(charId, 'Spell Slot', slotLevel);
  host.showToast(`Expended level ${slotLevel} spell slot (${remaining} remaining)`);
}

export async function handleSheetRestoreSlot(host: any, charId: string, e: CustomEvent) {
  const { slotLevel, remaining } = e.detail || {};
  await appDataService.restoreCharacterSpellSlot(charId, slotLevel);
  host.showToast(`Restored level ${slotLevel} spell slot (${remaining} remaining)`);
}
