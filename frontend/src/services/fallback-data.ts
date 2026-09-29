import type { CharacterItem } from '@runefoble/character-sheet-ui';
import {
  FALLBACK_CAMPAIGNS,
  FALLBACK_CHARACTERS,
} from './app-data-service.fixtures.ts';

export { FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS };

export const FALLBACK_CHARACTER_DETAILS_CACHE: Map<string, any> = new Map();

export function getOrCreateFallbackCharacterDetail(char: CharacterItem | undefined, characterId: string): any {
  if (FALLBACK_CHARACTER_DETAILS_CACHE.has(characterId)) {
    return FALLBACK_CHARACTER_DETAILS_CACHE.get(characterId);
  }
  const detail = buildFallbackCharacterDetail(char, characterId);
  FALLBACK_CHARACTER_DETAILS_CACHE.set(characterId, detail);
  return detail;
}

// Fallback character roster includes: 'char-valeros', 'char-kyra', 'char-ezren'
export function buildFallbackCharacterDetail(char: CharacterItem | undefined, characterId: string): any {
  const c = char || {
    id: characterId || 'char-valeros',
    name: `Character #${characterId}`,
    characterClass: 'Adventurer',
    subclass: '',
    level: 1,
    currentHp: 10,
    maxHp: 10,
    armorClass: 10,
    speed: 30,
    campaignId: null,
    campaignTitle: null,
  };

  return {
    id: c.id,
    character_id: c.id,
    name: c.name,
    character_class: c.characterClass + (c.subclass ? ` (${c.subclass})` : ''),
    characterClass: c.characterClass,
    subclass: c.subclass,
    level: c.level,
    current_hp: c.currentHp,
    currentHp: c.currentHp,
    max_hp: c.maxHp,
    maxHp: c.maxHp,
    armor_class: c.armorClass,
    armorClass: c.armorClass,
    speed: c.speed || 30,
    speed_ft: c.speed || 30,
    equipment: {
      main_hand: 'Longsword +1',
      off_hand: 'Steel Shield',
      armor: 'Chain Mail',
      accessory: 'Ring of Protection',
    },
    inventory: [
      { item_id: 'i-1', name: 'Longsword +1', quantity: 1, weight_lbs: 3.0, slot: 'main_hand' },
      { item_id: 'i-2', name: 'Steel Shield', quantity: 1, weight_lbs: 6.0, slot: 'off_hand' },
      { item_id: 'i-3', name: 'Chain Mail', quantity: 1, weight_lbs: 55.0, slot: 'armor' },
      { item_id: 'i-4', name: 'Ring of Protection', quantity: 1, weight_lbs: 0.1, slot: 'accessory' },
      { item_id: 'i-5', name: 'Healing Potion', quantity: 3, weight_lbs: 0.5 },
      { item_id: 'i-6', name: 'Rations (5 days)', quantity: 5, weight_lbs: 2.0 },
    ],
    conditions: {},
    penalties: {},
    spell_slots: { 1: 4, 2: 2 },
    max_spell_slots: { 1: 4, 2: 2 },
    prepared_spells: ['Magic Missile', 'Shield'],
    spellbook: ['Magic Missile', 'Shield', 'Detect Magic', 'Misty Step'],
    stand_in_guardrails: {
      preserve_spell_slots: { 1: 1 },
      protect_allies: ['Valeros'],
      protect_ally_hp_threshold: 0.3,
      risk_threshold: 'cautious',
      avoid_melee: true,
      permadeath_safeguard: true,
      custom_priorities: ['Protect allies when low on HP'],
    },
    is_stand_in_active: Boolean(c.isAiStandIn),
    isAiStandIn: Boolean(c.isAiStandIn),
  };
}
