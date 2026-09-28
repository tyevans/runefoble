/**
 * Runefoble App Data Service Fallback Constants
 * ADR-0004, ADR-0007, TASK-0257
 */

import type { CampaignItem } from '@runefoble/game-session-ui';
import type { CharacterItem } from '@runefoble/character-sheet-ui';

export const FALLBACK_CAMPAIGNS: CampaignItem[] = [
  {
    id: '4',
    title: 'Tomb of the Star-Eater',
    description: 'Ancient celestial horrors slumber beneath the irradiated astral sands.',
    setting: 'Spelljammer Astral Void',
    system: '5e',
    role: 'owner',
    owner_id: 'user-valeros',
    dm_name: 'The Watcher',
    player_count: 4,
    has_active_session: true,
    active_session_id: 'session-tomb-14',
  },
  {
    id: '5',
    title: 'Whispering Depths',
    description: 'Subterranean aquatic expeditions through forgotten dwarven aqueducts.',
    setting: 'Underdark Aquatics',
    system: '5e',
    role: 'player',
    owner_id: 'user-evelyn',
    dm_name: 'Evelyn Vance',
    player_count: 5,
    has_active_session: false,
  },
];

export const FALLBACK_CHARACTERS: CharacterItem[] = [
  {
    id: 'char-valeros',
    name: 'Valeros of Korvosa',
    characterClass: 'Fighter',
    subclass: 'Battle Master',
    level: 4,
    currentHp: 38,
    maxHp: 45,
    armorClass: 18,
    speed: 30,
    campaignId: '4',
    campaignTitle: 'Tomb of the Star-Eater',
    portraitUrl: '/assets/portraits/fighter.svg',
  },
  {
    id: 'char-kyra',
    name: 'Kyra the Sun Maiden',
    characterClass: 'Cleric',
    subclass: 'Life Domain',
    level: 4,
    currentHp: 28,
    maxHp: 32,
    armorClass: 16,
    speed: 25,
    campaignId: '4',
    campaignTitle: 'Tomb of the Star-Eater',
    portraitUrl: '/assets/portraits/cleric.svg',
  },
  {
    id: 'char-ezren',
    name: 'Ezren the Gray',
    characterClass: 'Wizard',
    subclass: 'Evocation',
    level: 5,
    currentHp: 22,
    maxHp: 26,
    armorClass: 12,
    speed: 30,
    campaignId: null,
    campaignTitle: null,
    portraitUrl: '/assets/portraits/wizard.svg',
  },
];
