/**
 * Character Sub-Resource Mutations Client.
 *
 * Maps character sheet actions onto gateway-api sub-resource calls. Every call returns the
 * gateway result. Callers update local UI state only after an ok result (TASK-0640).
 * TASK-0356: Character Sheet Sub-Resource Mutations & Event-Sourced Persistence Integration.
 */

import { dataFailure, type DataResult } from './data-result.ts';

export interface MutationHost {
  apiBase: string;
  request<T>(path: string, init?: RequestInit): Promise<DataResult<T>>;
}

export function mutateCharacterHealth(host: MutationHost, characterId: string, delta: number, source = 'damage'): Promise<DataResult<any>> {
  return host.request<any>(`${host.apiBase}/characters/${characterId}/health`, {
    method: 'POST',
    body: JSON.stringify({ delta, source }),
  });
}

export function mutateCharacterEquip(host: MutationHost, characterId: string, slot: string, itemName: string): Promise<DataResult<any>> {
  return host.request<any>(`${host.apiBase}/characters/${characterId}/equipment`, {
    method: 'POST',
    body: JSON.stringify({ slot, item_name: itemName }),
  });
}

export function mutateCharacterUnequip(host: MutationHost, characterId: string, slot: string): Promise<DataResult<any>> {
  return host.request<any>(`${host.apiBase}/characters/${characterId}/equipment/${slot}`, { method: 'DELETE' });
}

export function mutateCharacterAddInventory(host: MutationHost, characterId: string, item: any): Promise<DataResult<any>> {
  const itemId = item.item_id || item.itemId || `inv-${Date.now()}`;
  const name = item.name || 'Unknown Item';
  const quantity = item.quantity || 1;
  const weightLbs = item.weight_lbs ?? item.weightLbs ?? item.weight ?? 1.0;
  return host.request<any>(`${host.apiBase}/characters/${characterId}/inventory`, {
    method: 'POST',
    body: JSON.stringify({ item_id: itemId, name, quantity, weight_lbs: weightLbs, slot: item.slot }),
  });
}

export function mutateCharacterRemoveInventory(host: MutationHost, characterId: string, itemId: string, quantity = 1): Promise<DataResult<any>> {
  return host.request<any>(`${host.apiBase}/characters/${characterId}/inventory/${itemId}?quantity=${quantity}`, { method: 'DELETE' });
}

export function mutateCharacterApplyCondition(host: MutationHost, characterId: string, condition: string, source = 'tactical'): Promise<DataResult<any>> {
  return host.request<any>(`${host.apiBase}/characters/${characterId}/conditions`, {
    method: 'POST',
    body: JSON.stringify({ condition, source }),
  });
}

export function mutateCharacterRemoveCondition(host: MutationHost, characterId: string, condition: string): Promise<DataResult<any>> {
  return host.request<any>(`${host.apiBase}/characters/${characterId}/conditions/${condition}`, { method: 'DELETE' });
}

export function mutateCharacterCastSpell(host: MutationHost, characterId: string, spellName: string, slotLevel = 1): Promise<DataResult<any>> {
  return host.request<any>(`${host.apiBase}/characters/${characterId}/spells/cast`, {
    method: 'POST',
    body: JSON.stringify({ spell_name: spellName, slot_level: slotLevel }),
  });
}

export function mutateCharacterPrepareSpell(host: MutationHost, characterId: string, spellName: string, isPrepared = true): Promise<DataResult<any>> {
  return host.request<any>(`${host.apiBase}/characters/${characterId}/spells/prepare`, {
    method: 'POST',
    body: JSON.stringify({ spell_name: spellName, is_prepared: isPrepared }),
  });
}

/** No gateway route exists for restoring a spell slot yet. Reports the gap instead of faking success. */
export function mutateCharacterRestoreSlot(_host: MutationHost, _characterId: string, _slotLevel: number): Promise<DataResult<any>> {
  return Promise.resolve(dataFailure(501, 'Restoring spell slots is not available on the server yet.'));
}

export function mutateCharacterGuardrails(host: MutationHost, characterId: string, payload: any): Promise<DataResult<any>> {
  return host.request<any>(`${host.apiBase}/characters/${characterId}/guardrails`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}
