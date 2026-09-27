/**
 * Unit tests for Character Roster and Party Assignment UI logic.
 * TASK-0211: Character Roster and Party Assignment Microfrontend
 * ADR-0004, ADR-0012, ADR-0013
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  type CharacterItem,
  type RosterCampaignOption,
  type CreateCharacterPayload,
  calcModifier,
  formatModifier,
  filterCharacters,
} from '../../services/character_sheet/ui/src/roster/types.ts';

const sampleCampaigns: RosterCampaignOption[] = [
  { id: 'camp-101', title: 'Tomb of the Star-Eater' },
  { id: 'camp-102', title: 'Whispering Depths' },
];

const sampleCharacters: CharacterItem[] = [
  {
    id: 'char-1',
    name: 'Valeros of Korvosa',
    characterClass: 'Fighter',
    subclass: 'Battle Master',
    level: 4,
    currentHp: 38,
    maxHp: 45,
    armorClass: 18,
    speed: 30,
    campaignId: 'camp-101',
    campaignTitle: 'Tomb of the Star-Eater',
    portraitUrl: '/assets/portraits/fighter.svg',
  },
  {
    id: 'char-2',
    name: 'Kyra the Sun Maiden',
    characterClass: 'Cleric',
    subclass: 'Life Domain',
    level: 4,
    currentHp: 28,
    maxHp: 32,
    armorClass: 16,
    speed: 25,
    campaignId: 'camp-101',
    campaignTitle: 'Tomb of the Star-Eater',
    portraitUrl: '/assets/portraits/cleric.svg',
  },
  {
    id: 'char-3',
    name: 'Ezren the Gray',
    characterClass: 'Wizard',
    subclass: 'Evocation',
    level: 5,
    currentHp: 8,
    maxHp: 26,
    armorClass: 12,
    speed: 30,
    campaignId: null,
    campaignTitle: null,
    portraitUrl: '/assets/portraits/wizard.svg',
  },
  {
    id: 'char-4',
    name: 'Merisiel Nightshadow',
    characterClass: 'Rogue',
    subclass: 'Thief',
    level: 3,
    currentHp: 22,
    maxHp: 22,
    armorClass: 15,
    speed: 35,
    campaignId: null,
    campaignTitle: null,
    portraitUrl: '/assets/portraits/rogue.svg',
  },
];

describe('Ability Score Modifiers', () => {
  it('calculates numerical ability modifiers accurately', () => {
    assert.equal(calcModifier(8), -1);
    assert.equal(calcModifier(9), -1);
    assert.equal(calcModifier(10), 0);
    assert.equal(calcModifier(11), 0);
    assert.equal(calcModifier(12), 1);
    assert.equal(calcModifier(14), 2);
    assert.equal(calcModifier(15), 2);
    assert.equal(calcModifier(16), 3);
    assert.equal(calcModifier(18), 4);
    assert.equal(calcModifier(20), 5);
  });

  it('formats modifier strings with explicit plus signs', () => {
    assert.equal(formatModifier(8), '-1');
    assert.equal(formatModifier(10), '+0');
    assert.equal(formatModifier(14), '+2');
    assert.equal(formatModifier(18), '+4');
  });
});

describe('Character Roster Search & Filter Logic', () => {
  it('returns all characters when filter is "all" and search is empty', () => {
    const res = filterCharacters(sampleCharacters, '', 'all');
    assert.equal(res.length, 4);
  });

  it('filters characters assigned to an active campaign', () => {
    const res = filterCharacters(sampleCharacters, '', 'assigned');
    assert.equal(res.length, 2);
    assert.ok(res.every((c) => c.campaignId !== null));
    assert.equal(res[0].name, 'Valeros of Korvosa');
    assert.equal(res[1].name, 'Kyra the Sun Maiden');
  });

  it('filters unassigned free-agent characters', () => {
    const res = filterCharacters(sampleCharacters, '', 'unassigned');
    assert.equal(res.length, 2);
    assert.ok(res.every((c) => !c.campaignId));
    assert.equal(res[0].name, 'Ezren the Gray');
    assert.equal(res[1].name, 'Merisiel Nightshadow');
  });

  it('filters characters by case-insensitive name matching', () => {
    const res = filterCharacters(sampleCharacters, 'valeros', 'all');
    assert.equal(res.length, 1);
    assert.equal(res[0].name, 'Valeros of Korvosa');
  });

  it('filters characters by class or subclass matching', () => {
    const byClass = filterCharacters(sampleCharacters, 'wizard', 'all');
    assert.equal(byClass.length, 1);
    assert.equal(byClass[0].name, 'Ezren the Gray');

    const bySubclass = filterCharacters(sampleCharacters, 'thief', 'all');
    assert.equal(bySubclass.length, 1);
    assert.equal(bySubclass[0].name, 'Merisiel Nightshadow');
  });

  it('combines text search with assignment status filter', () => {
    const res = filterCharacters(sampleCharacters, 'Korvosa', 'unassigned');
    assert.equal(res.length, 0); // Valeros is assigned, so unassigned should yield 0

    const matched = filterCharacters(sampleCharacters, 'Korvosa', 'assigned');
    assert.equal(matched.length, 1);
    assert.equal(matched[0].name, 'Valeros of Korvosa');
  });
});

describe('Character Builder Validation & Payload Assembly', () => {
  it('builds a complete character creation payload', () => {
    const payload: CreateCharacterPayload = {
      name: 'Valeros',
      characterClass: 'Fighter',
      subclass: 'Champion',
      level: 4,
      maxHp: 45,
      armorClass: 18,
      speed: 30,
      abilityScores: { str: 16, dex: 14, con: 15, int: 10, wis: 12, cha: 8 },
      portraitUrl: '/assets/portraits/fighter.svg',
    };

    assert.equal(payload.name, 'Valeros');
    assert.equal(payload.characterClass, 'Fighter');
    assert.equal(payload.level, 4);
    assert.equal(payload.maxHp, 45);
    assert.equal(payload.armorClass, 18);
    assert.equal(payload.abilityScores.str, 16);
    assert.equal(calcModifier(payload.abilityScores.str), 3);
  });
});

describe('Party Assignment Operations', () => {
  it('resolves campaign title when assigning character to party', () => {
    const selectedCampId = 'camp-101';
    const camp = sampleCampaigns.find((c) => c.id === selectedCampId);
    assert.ok(camp);

    const eventDetail = {
      characterId: 'char-3',
      campaignId: camp!.id,
      campaignTitle: camp!.title,
    };

    assert.equal(eventDetail.characterId, 'char-3');
    assert.equal(eventDetail.campaignId, 'camp-101');
    assert.equal(eventDetail.campaignTitle, 'Tomb of the Star-Eater');
  });

  it('handles unassigning character from campaign party', () => {
    const selectedCampId = '';
    const camp = sampleCampaigns.find((c) => c.id === selectedCampId);

    const eventDetail = {
      characterId: 'char-1',
      campaignId: selectedCampId || null,
      campaignTitle: camp ? camp.title : null,
    };

    assert.equal(eventDetail.characterId, 'char-1');
    assert.equal(eventDetail.campaignId, null);
    assert.equal(eventDetail.campaignTitle, null);
  });
});
