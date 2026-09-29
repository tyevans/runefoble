/**
 * Frontend Blackbox Test Suite: Dynamic Campaign Sessions Scoping, Scheduling & Offline Cache.
 * TASK-0354: Dynamic Campaign Sessions Scoping, Scheduling & Offline Cache.
 * Governing ADRs: ADR-0004, ADR-0007, ADR-0013.
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { AppDataService, appDataService } from '../src/services/app-data-service.ts';
import {
  FALLBACK_CAMPAIGN_SESSIONS_MAP,
  getFallbackCampaignSessions,
  getFallbackSession,
} from '../src/services/app-data-service.fixtures.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SERVICES_DIR = resolve(__dirname, '../src/services');
const DATA_SERVICE_FILE = resolve(SERVICES_DIR, 'app-data-service.ts');
const FIXTURES_FILE = resolve(SERVICES_DIR, 'app-data-service.fixtures.ts');

describe('TASK-0354: File Length Invariants (Hard Invariant 6)', () => {
  it('verifies app-data-service.ts is strictly < 220 lines', () => {
    const lines = readFileSync(DATA_SERVICE_FILE, 'utf-8').split('\n').length;
    assert.ok(lines < 220, `app-data-service.ts has ${lines} lines, expected < 220`);
  });

  it('verifies app-data-service.fixtures.ts is strictly < 160 lines', () => {
    const lines = readFileSync(FIXTURES_FILE, 'utf-8').split('\n').length;
    assert.ok(lines < 160, `app-data-service.fixtures.ts has ${lines} lines, expected < 160`);
  });
});

describe('TASK-0354: Campaign Sessions Scoping and Stub Eradication', () => {
  it('eradicates universal "Session #15: Chamber of Horrors" from new campaigns', () => {
    const newCampId = `test-camp-${Date.now()}`;
    const sessions = getFallbackCampaignSessions(newCampId);
    assert.ok(sessions.length >= 1);
    assert.strictEqual(sessions[0].title, 'Session #1: Assembly & Briefing');
    assert.strictEqual(sessions[0].status, 'lobby');
    assert.ok(!sessions.some((s) => s.title === 'Session #15: Chamber of Horrors'));
  });

  it('maintains expected scoped session rosters for legacy seeded campaigns', () => {
    const camp4Sessions = getFallbackCampaignSessions('4');
    assert.strictEqual(camp4Sessions.length, 2);
    assert.ok(camp4Sessions.some((s) => s.title === 'Session #14: Tomb of the Star-Eater' && s.status === 'active'));
    assert.ok(camp4Sessions.some((s) => s.title === 'Session #15: Chamber of Horrors' && s.status === 'lobby'));

    const camp5Sessions = getFallbackCampaignSessions('5');
    assert.strictEqual(camp5Sessions.length, 1);
    assert.strictEqual(camp5Sessions[0].title, 'Session #1: The Sunken Aqueduct');
    assert.strictEqual(camp5Sessions[0].status, 'upcoming');
  });

  it('enforces non-overlapping session rosters across independent campaigns', () => {
    const campASessions = getFallbackCampaignSessions('alpha-99');
    const campBSessions = getFallbackCampaignSessions('beta-99');

    assert.notStrictEqual(campASessions, campBSessions);
    assert.ok(campASessions.every((s) => s.campaignId === 'alpha-99'));
    assert.ok(campBSessions.every((s) => s.campaignId === 'beta-99'));
  });
});

describe('TASK-0354: Offline / Fallback Session Cache Persistence', () => {
  it('persists newly scheduled sessions across fetchCampaignSessions reloads', async () => {
    const campId = `persist-camp-${Date.now()}`;
    const initialSessions = await appDataService.fetchCampaignSessions(campId);
    assert.strictEqual(initialSessions.length, 1);
    assert.strictEqual(initialSessions[0].title, 'Session #1: Assembly & Briefing');

    const created = await appDataService.createCampaignSession(campId, {
      title: 'Chapter 2: The Crypt of the Undying',
      status: 'upcoming',
      scheduled_at: '2026-11-01T18:00:00Z',
      description: 'Dungeon infiltration past the skeletal sentinels.',
    });
    assert.ok(created.id);
    assert.strictEqual(created.campaignId, campId);
    assert.strictEqual(created.title, 'Chapter 2: The Crypt of the Undying');
    assert.strictEqual(created.status, 'upcoming');

    // Simulate subsequent view load or page reload
    const reloadedSessions = await appDataService.fetchCampaignSessions(campId);
    assert.strictEqual(reloadedSessions.length, 2);
    const titles = reloadedSessions.map((s) => s.title);
    assert.ok(titles.includes('Session #1: Assembly & Briefing'));
    assert.ok(titles.includes('Chapter 2: The Crypt of the Undying'));

    // Verify session retrieval by ID
    const fetchedDetail = await appDataService.fetchSession(created.id);
    assert.ok(fetchedDetail);
    assert.strictEqual(fetchedDetail.id, created.id);
    assert.strictEqual(fetchedDetail.title, 'Chapter 2: The Crypt of the Undying');
  });

  it('auto-seeds staging lobby session when creating new campaign in fallback mode', async () => {
    const createdCamp = await appDataService.createCampaign({
      title: 'Voyage of the Astral Galleon',
      setting: 'Spelljammer Wildspace',
      system: '5e',
    });
    assert.ok(createdCamp.id);

    const sessions = await appDataService.fetchCampaignSessions(createdCamp.id);
    assert.strictEqual(sessions.length, 1);
    assert.strictEqual(sessions[0].title, 'Session #1: Assembly & Briefing');
    assert.strictEqual(sessions[0].status, 'lobby');
  });
});
