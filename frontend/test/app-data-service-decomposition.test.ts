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
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { AppDataService, appDataService } from '../src/services/app-data-service.ts';
import {
  FALLBACK_CAMPAIGNS,
  FALLBACK_CHARACTERS,
  FALLBACK_MEMBERS,
  FALLBACK_PARTICIPANTS,
  FALLBACK_SESSIONS,
} from './support/app-data-service.fixtures.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SRC_DIR = resolve(__dirname, '../src');
const DATA_SERVICE_FILE = resolve(SRC_DIR, 'services/app-data-service.ts');
const FIXTURES_FILE = resolve(__dirname, 'support/app-data-service.fixtures.ts');
const RETIRED_FALLBACK_FILE = resolve(SRC_DIR, 'fixtures/fallback-data.ts');
const RETIRED_SERVICE_FIXTURES = resolve(SRC_DIR, 'services/app-data-service.fixtures.ts');

function lineCount(path: string): number {
  return readFileSync(path, 'utf-8').split('\n').length;
}

describe('TASK-0271: File Length Invariants (Hard Invariant 6)', () => {
  it('verifies app-data-service.ts is strictly < 220 lines', () => {
    const lines = lineCount(DATA_SERVICE_FILE);
    assert.ok(lines < 220, `app-data-service.ts has ${lines} lines, which must be strictly < 220 lines`);
  });

  it('verifies app-data-service.fixtures.ts is strictly < 160 lines', () => {
    const lines = lineCount(FIXTURES_FILE);
    assert.ok(lines < 160, `app-data-service.fixtures.ts has ${lines} lines, which must be strictly < 160 lines`);
  });
});

describe('TASK-0640: Fixture Relocation', () => {
  it('keeps the fixture module under test/support/ with its canned arrays for tests and stories', () => {
    assert.ok(Array.isArray(FALLBACK_CAMPAIGNS) && FALLBACK_CAMPAIGNS.length >= 2);
    assert.ok(Array.isArray(FALLBACK_CHARACTERS) && FALLBACK_CHARACTERS.length >= 3);
    assert.ok(Array.isArray(FALLBACK_MEMBERS) && FALLBACK_MEMBERS.length >= 3);
    assert.ok(Array.isArray(FALLBACK_PARTICIPANTS) && FALLBACK_PARTICIPANTS.length >= 2);
    assert.ok(Array.isArray(FALLBACK_SESSIONS) && FALLBACK_SESSIONS.length >= 2);
  });

  it('removes the old service-level fixture path and the fallback-data re-export shim', () => {
    assert.equal(existsSync(RETIRED_SERVICE_FIXTURES), false, 'services/app-data-service.fixtures.ts must not exist');
    assert.equal(existsSync(RETIRED_FALLBACK_FILE), false, 'fixtures/fallback-data.ts must not exist');
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
