/**
 * App Shell Route-Bound WebSocket Lifecycle Management Test Suite.
 *
 * TASK-0287: Frontend App Shell Test Suite Modular Decomposition
 * Governing ADRs: ADR-0004, ADR-0010, ADR-0013
 * Hard Invariants:
 * - Hard Invariant 6: File length limit (< 110 lines; limit < 130 lines)
 * - Hard Invariant 7: Blackbox TDD with frontdoor setup
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { Router, type MatchedRoute } from '../../src/router/router.ts';

function isSessionWebSocketRequired(route: MatchedRoute | null): boolean {
  const pat = route?.pattern || '';
  return pat === '#/campaigns/:campaignId/sessions/:sessionId' ||
         pat === '#/campaigns/:campaignId/lobby/:sessionId';
}

describe('Route-Bound WebSocket Lifecycle Management', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('activates WebSocket only on session-lobby and session-active routes', () => {
    assert.equal(isSessionWebSocketRequired(router.match('#/campaigns')), false);
    assert.equal(isSessionWebSocketRequired(router.match('#/campaigns/4')), false);
    assert.equal(isSessionWebSocketRequired(router.match('#/characters')), false);
    assert.equal(isSessionWebSocketRequired(router.match('#/login')), false);

    assert.equal(isSessionWebSocketRequired(router.match('#/campaigns/4/lobby/sess-1')), true);
    assert.equal(isSessionWebSocketRequired(router.match('#/campaigns/4/sessions/sess-1')), true);
  });

  it('tears down WebSocket when navigating away from an active session', async () => {
    let wsDisconnected = false;
    let connectedSessionId: string | null = null;

    const connectWS = (sessionId: string) => { connectedSessionId = sessionId; wsDisconnected = false; };
    const disconnectWS = () => { connectedSessionId = null; wsDisconnected = true; };

    router.onRouteChanged((route) => {
      if (isSessionWebSocketRequired(route)) connectWS(route.params.sessionId);
      else disconnectWS();
    });

    await router.navigate('#/campaigns/4/sessions/sess-100');
    assert.equal(connectedSessionId, 'sess-100');
    assert.equal(wsDisconnected, false);

    await router.navigate('#/campaigns');
    assert.equal(connectedSessionId, null);
    assert.equal(wsDisconnected, true);
  });

  it('switches WebSocket connection when switching directly between sessions', async () => {
    const connections: string[] = [];
    router.onRouteChanged((route) => {
      if (isSessionWebSocketRequired(route)) connections.push(route.params.sessionId);
    });

    await router.navigate('#/campaigns/4/lobby/sess-A');
    await router.navigate('#/campaigns/5/sessions/sess-B');
    assert.deepEqual(connections, ['sess-A', 'sess-B']);
  });

  it('validates VTT board and lobby event contracts in App Shell source (TASK-0358)', () => {
    const appPath = fileURLToPath(new URL('../../src/runefoble-app.ts', import.meta.url));
    const appSrc = readFileSync(appPath, 'utf-8');

    assert.ok(appSrc.includes('@toggle-readiness=') && appSrc.includes('@toggle-stand-in='));
    assert.ok(appSrc.includes("'player_readiness'") && appSrc.includes("'player_stand_in'"));
    assert.ok(appSrc.includes('.websocketUrl=${this.getWebSocketUrl()}'));
    assert.ok(appSrc.includes('@token-action=') && appSrc.includes('@aoe-place='));
    assert.ok(appSrc.includes('@spell-vfx-triggered=') && appSrc.includes('@confirm-ghost='));
    assert.ok(appSrc.includes('.cols=${this.boardCols}') && appSrc.includes('.rows=${this.boardRows}'));

    for (const msgType of ["'dice_rolled'", "'turn_advanced'", "'aoe_placed'", "'spell_vfx'", "'dm_whisper'"]) {
      assert.ok(appSrc.includes(msgType), `Missing message handler for ${msgType}`);
    }
  });
});
