/**
 * Frontend Blackbox Test Suite: AppDataService Fixtures and Client Modular Decomposition.
 *
 * TASK-0271: Frontend App Data Service Fixtures and Client Modular Decomposition
 * Governing ADRs: ADR-0004, ADR-0007
 * Hard Invariants:
 * - Hard Invariant 6: File length limit (< 500 lines; app-data-service < 220 lines, fixtures < 160 lines)
 * - Hard Invariant 7: Blackbox TDD with frontdoor setup
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { AppDataService, appDataService } from '../src/services/app-data-service.ts';
import {
  FALLBACK_CAMPAIGNS,
  FALLBACK_CHARACTERS,
  FALLBACK_MEMBERS,
  FALLBACK_PARTICIPANTS,
  FALLBACK_SESSIONS,
  getFallbackCampaignSessions,
  getFallbackSession,
} from '../src/services/app-data-service.fixtures.ts';
import {
  FALLBACK_CAMPAIGNS as LEGACY_FALLBACK_CAMPAIGNS,
  FALLBACK_CHARACTERS as LEGACY_FALLBACK_CHARACTERS,
} from '../src/services/fallback-data.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SERVICES_DIR = resolve(__dirname, '../src/services');
const DATA_SERVICE_FILE = resolve(SERVICES_DIR, 'app-data-service.ts');
const FIXTURES_FILE = resolve(SERVICES_DIR, 'app-data-service.fixtures.ts');
const FALLBACK_DATA_FILE = resolve(SERVICES_DIR, 'fallback-data.ts');

describe('TASK-0271: File Length Invariants (Hard Invariant 6)', () => {
  it('verifies app-data-service.ts is strictly < 220 lines', () => {
    const content = readFileSync(DATA_SERVICE_FILE, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(
      lines < 220,
      `app-data-service.ts has ${lines} lines, which must be strictly < 220 lines`
    );
  });

  it('verifies app-data-service.fixtures.ts is strictly < 160 lines', () => {
    const content = readFileSync(FIXTURES_FILE, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(
      lines < 160,
      `app-data-service.fixtures.ts has ${lines} lines, which must be strictly < 160 lines`
    );
  });

  it('verifies fallback-data.ts is strictly < 200 lines', () => {
    const content = readFileSync(FALLBACK_DATA_FILE, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(
      lines < 200,
      `fallback-data.ts has ${lines} lines, which must be strictly < 200 lines`
    );
  });
});

describe('TASK-0271: Fixture Extraction & Re-export Integrity', () => {
  it('exports all 5 required fallback fixtures from app-data-service.fixtures.ts', () => {
    assert.ok(Array.isArray(FALLBACK_CAMPAIGNS), 'FALLBACK_CAMPAIGNS must be an array');
    assert.ok(Array.isArray(FALLBACK_CHARACTERS), 'FALLBACK_CHARACTERS must be an array');
    assert.ok(Array.isArray(FALLBACK_MEMBERS), 'FALLBACK_MEMBERS must be an array');
    assert.ok(Array.isArray(FALLBACK_PARTICIPANTS), 'FALLBACK_PARTICIPANTS must be an array');
    assert.ok(Array.isArray(FALLBACK_SESSIONS), 'FALLBACK_SESSIONS must be an array');

    assert.ok(FALLBACK_CAMPAIGNS.length >= 2, 'Must have at least 2 fallback campaigns');
    assert.ok(FALLBACK_CHARACTERS.length >= 3, 'Must have at least 3 fallback characters');
    assert.ok(FALLBACK_MEMBERS.length >= 3, 'Must have at least 3 fallback members');
    assert.ok(FALLBACK_PARTICIPANTS.length >= 2, 'Must have at least 2 fallback participants');
    assert.ok(FALLBACK_SESSIONS.length >= 2, 'Must have at least 2 fallback sessions');
  });

  it('preserves backward compatibility by sharing instances with fallback-data.ts', () => {
    assert.strictEqual(
      FALLBACK_CAMPAIGNS,
      LEGACY_FALLBACK_CAMPAIGNS,
      'FALLBACK_CAMPAIGNS in fallback-data.ts must reference the same array as fixtures'
    );
    assert.strictEqual(
      FALLBACK_CHARACTERS,
      LEGACY_FALLBACK_CHARACTERS,
      'FALLBACK_CHARACTERS in fallback-data.ts must reference the same array as fixtures'
    );
  });

  it('resolves campaign sessions and session item through helper functions', () => {
    const sessions = getFallbackCampaignSessions('4');
    assert.ok(sessions.length >= 2);
    assert.strictEqual(sessions[0].id, 'session-tomb-14');

    const session = getFallbackSession('session-tomb-14');
    assert.strictEqual(session.id, 'session-tomb-14');
    assert.strictEqual(session.title, 'Session #14: Tomb of the Star-Eater');
    assert.strictEqual(session.status, 'active');
  });
});

describe('TASK-0271: AppDataService Public Frontdoor Functionality', () => {
  it('returns singleton instance of AppDataService', () => {
    const instance1 = AppDataService.getInstance();
    const instance2 = AppDataService.getInstance();
    assert.strictEqual(instance1, instance2);
    assert.strictEqual(instance1, appDataService);
  });

  it('fetches campaigns and returns fallback list when unintercepted', async () => {
    const campaigns = await appDataService.fetchCampaigns();
    assert.ok(Array.isArray(campaigns));
    assert.ok(campaigns.length >= 2);
    assert.ok(campaigns.some((c) => c.title === 'Tomb of the Star-Eater'));
  });

  it('fetches single campaign by ID', async () => {
    const campaign = await appDataService.fetchCampaign('4');
    assert.ok(campaign);
    assert.strictEqual(campaign.id, '4');
    assert.strictEqual(campaign.title, 'Tomb of the Star-Eater');
  });

  it('fetches campaign members', async () => {
    const members = await appDataService.fetchCampaignMembers('4');
    assert.ok(Array.isArray(members));
    assert.strictEqual(members.length, 3);
    assert.strictEqual(members[0].username, 'Valeros (You)');
  });

  it('fetches campaign sessions and individual session', async () => {
    const sessions = await appDataService.fetchCampaignSessions('4');
    assert.ok(Array.isArray(sessions));
    assert.ok(sessions.length >= 2);

    const session = await appDataService.fetchSession('session-tomb-14');
    assert.ok(session);
    assert.strictEqual(session.id, 'session-tomb-14');
  });

  it('fetches characters and character detail', async () => {
    const chars = await appDataService.fetchCharacters();
    assert.ok(Array.isArray(chars));
    assert.ok(chars.length >= 3);

    const valeros = await appDataService.fetchCharacter('char-valeros');
    assert.ok(valeros);
    assert.strictEqual(valeros.name, 'Valeros of Korvosa');
    assert.strictEqual(valeros.characterClass, 'Fighter');
  });

  it('fetches lobby state with participants and sorted available characters', async () => {
    const lobby = await appDataService.fetchLobbyState('session-tomb-14', '4');
    assert.ok(lobby.participants);
    assert.ok(lobby.availableCharacters);
    assert.ok(lobby.participants.length >= 2);
    assert.strictEqual(lobby.participants[0].characterName, 'Valeros of Korvosa');
  });

  it('fetches board tokens and session events', async () => {
    const tokens = await appDataService.fetchBoardTokens('session-tomb-14');
    assert.ok(tokens.length >= 4);
    assert.strictEqual(tokens[0].name, 'Valeros');

    const events = await appDataService.fetchSessionEvents('session-tomb-14');
    assert.ok(events.length >= 3);
    assert.strictEqual(events[0].source, 'watcher_dm');
  });

  it('supports character creation, campaign assignment, and deletion lifecycle', async () => {
    const initialCount = (await appDataService.fetchCharacters()).length;
    const newChar = await appDataService.createCharacter({
      name: 'Harsk the Ranger',
      characterClass: 'Ranger',
      subclass: 'Hunter',
      level: 3,
      maxHp: 28,
      armorClass: 15,
      speed: 30,
    });
    assert.ok(newChar.id);
    assert.strictEqual(newChar.name, 'Harsk the Ranger');

    const afterCreateCount = (await appDataService.fetchCharacters()).length;
    assert.strictEqual(afterCreateCount, initialCount + 1);

    await appDataService.assignCharacterCampaign(newChar.id, '4');
    const updatedChars = await appDataService.fetchCharacters();
    const found = updatedChars.find((c) => c.id === newChar.id);
    assert.ok(found);
    assert.strictEqual(found.campaignId, '4');

    await appDataService.deleteCharacter(newChar.id);
    const afterDeleteCount = (await appDataService.fetchCharacters()).length;
    assert.strictEqual(afterDeleteCount, initialCount);
  });
});
