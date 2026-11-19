/**
 * Character Sheet Action Event Handlers.
 *
 * Dispatches character sub-resource mutations from <runefoble-character-sheet>
 * to appDataService. Local view state changes only after the gateway confirms the write.
 * A failed write shows a toast with the server message and leaves the sheet unchanged (TASK-0640).
 * A confirmed write puts a new character object on the host. It never changes the old
 * object, because Lit renders a child again only for a new reference (TASK-0908).
 * TASK-0356: Character Sheet Sub-Resource Mutations & Event-Sourced Persistence Integration.
 */

import { appDataService } from './services/app-data-service.ts';
import type { DataResult } from './services/data-result.ts';

export interface SheetAppHost {
  selectedCharacter: any;
  characters: any[];
  activeCharacter: any;
  sessionId?: string;
  showToast(message: string): void;
}

/** Runs a gateway write. On failure, shows the server message and returns false. */
async function commit<T>(host: { showToast(message: string): void }, call: Promise<DataResult<T>>): Promise<boolean> {
  const result = await call;
  if (!result.ok) {
    host.showToast(`Not saved. ${result.message}`);
    return false;
  }
  return true;
}

/** Puts a new selected character on the host, built from the old one and a patch. */
function patchSelected(host: SheetAppHost, patch: (c: any) => Record<string, unknown>): void {
  const c = host.selectedCharacter;
  if (c) host.selectedCharacter = { ...c, ...patch(c) };
}

function listOf(value: unknown): any[] {
  if (Array.isArray(value)) return value;
  return Object.values((value as Record<string, unknown>) || {});
}

export async function handleSheetHpChange(host: SheetAppHost, charId: string, e: CustomEvent) {
  const { delta, currentHp, maxHp } = e.detail || {};
  if (!(await commit(host, appDataService.modifyCharacterHealth(charId, delta)))) return;
  patchSelected(host, () => ({ currentHp, current_hp: currentHp }));
  host.characters = host.characters.map((c: any) => (c.id === charId ? { ...c, currentHp } : c));
  if (host.activeCharacter?.id === charId) host.activeCharacter = { ...host.activeCharacter, currentHp };
  host.showToast(delta >= 0 ? `Healed ${delta} HP (${currentHp}/${maxHp})` : `Took ${Math.abs(delta)} damage (${currentHp}/${maxHp})`);
}

export async function handleSheetEquipItem(host: SheetAppHost, charId: string, e: CustomEvent) {
  const { slot, itemName } = e.detail || {};
  if (!(await commit(host, appDataService.equipCharacterItem(charId, slot, itemName)))) return;
  patchSelected(host, (c) => ({ equipment: { ...(c.equipment || {}), [slot]: itemName } }));
  host.showToast(`Equipped ${itemName} to ${slot.replace('_', ' ')}`);
}

export async function handleSheetUnequipItem(host: SheetAppHost, charId: string, e: CustomEvent) {
  const { slot, itemName } = e.detail || {};
  if (!(await commit(host, appDataService.unequipCharacterItem(charId, slot)))) return;
  patchSelected(host, (c) => {
    const { [slot]: _removed, ...equipment } = c.equipment || {};
    return { equipment };
  });
  host.showToast(`Unequipped ${itemName || slot.replace('_', ' ')}`);
}

export async function handleSheetAddItem(host: SheetAppHost, charId: string, e: CustomEvent) {
  const { item } = e.detail || {};
  if (!item) return;
  if (!(await commit(host, appDataService.addCharacterInventoryItem(charId, item)))) return;
  patchSelected(host, (c) => ({ inventory: [...listOf(c.inventory), item] }));
  host.showToast(`Added ${item.name} to inventory`);
}

export async function handleSheetRemoveItem(host: SheetAppHost, charId: string, e: CustomEvent) {
  const { itemId, itemName } = e.detail || {};
  if (!(await commit(host, appDataService.removeCharacterInventoryItem(charId, itemId)))) return;
  patchSelected(host, (c) => ({ inventory: listOf(c.inventory).filter((i: any) => i.item_id !== itemId && i.itemId !== itemId) }));
  host.showToast(`Removed ${itemName || 'item'} from inventory`);
}

export async function handleSheetCastSpell(host: SheetAppHost, charId: string, e: CustomEvent) {
  const { spellName, slotLevel } = e.detail || {};
  if (!(await commit(host, appDataService.castCharacterSpell(charId, spellName, slotLevel)))) return;
  patchSelected(host, (c) => {
    const key = c.spellSlots ? 'spellSlots' : 'spell_slots';
    const slots = c[key];
    if (!slots || !(slots[slotLevel] > 0)) return {};
    return { [key]: { ...slots, [slotLevel]: slots[slotLevel] - 1 } };
  });
  host.showToast(`Cast ${spellName} (Tier ${slotLevel})`);
}

export async function handleSheetPrepareSpell(host: SheetAppHost, charId: string, e: CustomEvent) {
  const { spellName, prepared } = e.detail || {};
  if (!(await commit(host, appDataService.prepareCharacterSpell(charId, spellName, prepared)))) return;
  patchSelected(host, (c) => {
    const key = c.preparedSpells ? 'preparedSpells' : 'prepared_spells';
    const list: string[] = c[key] || [];
    const next = prepared ? (list.includes(spellName) ? [...list] : [...list, spellName]) : list.filter((s) => s !== spellName);
    return { [key]: next };
  });
  host.showToast(prepared ? `Prepared ${spellName}` : `Unprepared ${spellName}`);
}

export async function handleSheetApplyCondition(host: SheetAppHost, charId: string, e: CustomEvent) {
  const { condition, source } = e.detail || {};
  if (!(await commit(host, appDataService.applyCharacterCondition(charId, condition, source)))) return;
  patchSelected(host, (c) => (Array.isArray(c.conditions)
    ? { conditions: [...c.conditions, { id: condition, name: condition, source: source || 'tactical' }] }
    : {}));
  host.showToast(`Condition ${condition} applied`);
}

export async function handleSheetRemoveCondition(host: SheetAppHost, charId: string, e: CustomEvent) {
  const { condition } = e.detail || {};
  if (!(await commit(host, appDataService.removeCharacterCondition(charId, condition)))) return;
  patchSelected(host, (c) => (Array.isArray(c.conditions)
    ? { conditions: c.conditions.filter((x: any) => (x.name || x.id) !== condition) }
    : {}));
  host.showToast(`Condition ${condition} removed`);
}

/** Saves stand-in guardrails. Shows success and the new guardrails only after the gateway confirms. */
export async function handleGuardrailsSaved(host: SheetAppHost, charId: string, e: CustomEvent) {
  if (!(await commit(host, appDataService.updateCharacterGuardrails(charId, e.detail)))) return;
  patchSelected(host, () => ({ stand_in_guardrails: e.detail, standInGuardrails: e.detail }));
  host.showToast('Tactical Guardrails Saved!');
}

/** Requests a hot-swap takeover. Shows the transfer text only after the gateway confirms. */
export async function handleHotSwapRequested(host: SheetAppHost, charId: string, e: CustomEvent) {
  const cId = e.detail?.characterId || charId;
  if (!(await commit(host, appDataService.requestHotSwap(host.sessionId ?? '', cId)))) return;
  host.showToast('Hot-Swap Takeover Requested: Control transferred to player!');
}

export async function handleSheetExpendSlot(host: SheetAppHost, charId: string, e: CustomEvent) {
  const { slotLevel, remaining } = e.detail || {};
  if (!(await commit(host, appDataService.castCharacterSpell(charId, 'Spell Slot', slotLevel)))) return;
  host.showToast(`Expended level ${slotLevel} spell slot (${remaining} remaining)`);
}

export async function handleSheetRestoreSlot(host: SheetAppHost, charId: string, e: CustomEvent) {
  const { slotLevel, remaining } = e.detail || {};
  if (!(await commit(host, appDataService.restoreCharacterSpellSlot(charId, slotLevel)))) return;
  host.showToast(`Restored level ${slotLevel} spell slot (${remaining} remaining)`);
}
