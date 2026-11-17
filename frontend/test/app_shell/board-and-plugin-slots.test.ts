/**
 * App Shell Board State & Plugin Slot Wiring Test Suite.
 *
 * TASK-0640b: Split from session-transitions.test.ts to keep each module under its line cap.
 * Governing ADRs: ADR-0004, ADR-0012, ADR-0013
 * Hard Invariants:
 * - Hard Invariant 6: File length limit (< 110 lines; limit < 130 lines)
 * - Hard Invariant 7: Blackbox TDD with frontdoor setup
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { AppDataService } from '../../src/services/app-data-service.ts';
import { registerDefaultPlugins, pluginRegistry } from '../../src/components/plugins/plugin_registry.ts';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';
import { FALLBACK_BOARD_TOKENS } from '../../src/fixtures/app-data-service.fixtures.ts';

describe('App Shell Board State & Plugin Slot Wiring', () => {
  let dataService: AppDataService;
  let gateway: FakeGateway;

  beforeEach(() => {
    dataService = new AppDataService();
    gateway = installFakeGateway({
      'GET /api/v1/boards/session-tomb-14': { body: { cols: 12, rows: 10, tokens: FALLBACK_BOARD_TOKENS } },
    });
  });

  afterEach(() => gateway.restore());

  it('provides dynamic board dimensions and tokens via fetchBoardState', async () => {
    const state = await dataService.fetchBoardState('session-tomb-14');
    assert.ok(state.ok);
    assert.ok(typeof state.data.cols === 'number' && typeof state.data.rows === 'number');
    assert.ok(Array.isArray(state.data.tokens) && state.data.tokens.length >= 1);
  });

  it('registers default tabletop plugins across standard slots for players and DM (TASK-0358)', () => {
    registerDefaultPlugins(pluginRegistry, false);
    assert.ok(pluginRegistry.getPluginsForSlot('hud-widget').some((p) => p.tag === 'runefoble-initiative-tracker'));
    assert.equal(pluginRegistry.getPluginsForSlot('sidebar-tool').some((p) => p.tag === 'runefoble-dm-whisper-bar'), false);
    registerDefaultPlugins(pluginRegistry, true);
    assert.ok(pluginRegistry.getPluginsForSlot('sidebar-tool').some((p) => p.tag === 'runefoble-dm-whisper-bar'));
  });
});
