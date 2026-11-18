/**
 * Frontend Blackbox Test Suite: AppDataService Fixtures and Client Modular Decomposition.
 *
 * TASK-0271: Frontend App Data Service Fixtures and Client Modular Decomposition
 * TASK-0640: Fixtures moved to src/fixtures/ and fallback-data.ts removed.
 * Governing ADRs: ADR-0004, ADR-0007
 * Hard Invariants:
 * - Hard Invariant 6: File length limit (< 500 lines; app-data-service < 220 lines, fixtures < 160 lines)
 * - Hard Invariant 7: Blackbox TDD with frontdoor setup
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { AppDataService, appDataService } from '../src/services/app-data-service.ts';
import {
  FALLBACK_CAMPAIGNS,
  FALLBACK_CHARACTERS,
  FALLBACK_MEMBERS,
  FALLBACK_PARTICIPANTS,
  FALLBACK_SESSIONS,
} from './support/app-data-service.fixtures.ts';


describe('TASK-0640: Fixture Relocation', () => {
  it('keeps the fixture module under test/support/ with its canned arrays for tests and stories', () => {
    assert.ok(Array.isArray(FALLBACK_CAMPAIGNS) && FALLBACK_CAMPAIGNS.length >= 2);
    assert.ok(Array.isArray(FALLBACK_CHARACTERS) && FALLBACK_CHARACTERS.length >= 3);
    assert.ok(Array.isArray(FALLBACK_MEMBERS) && FALLBACK_MEMBERS.length >= 3);
    assert.ok(Array.isArray(FALLBACK_PARTICIPANTS) && FALLBACK_PARTICIPANTS.length >= 2);
    assert.ok(Array.isArray(FALLBACK_SESSIONS) && FALLBACK_SESSIONS.length >= 2);
  });

});

describe('TASK-0271: AppDataService Public Frontdoor Functionality', () => {
  it('returns singleton instance of AppDataService', () => {
    const instance1 = AppDataService.getInstance();
    const instance2 = AppDataService.getInstance();
    assert.strictEqual(instance1, instance2);
    assert.strictEqual(instance1, appDataService);
  });
});
