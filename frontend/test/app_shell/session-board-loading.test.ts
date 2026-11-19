/**
 * Live session load without a board (TASK-0906).
 *
 * board_state answers 404 until a board exists for the session. The session route must still
 * load the chronicle feed, the roster and the campaign, and mark the board as `no_board`.
 * Other board failures still replace the view with the error state.
 * Governing ADRs: ADR-0013, ADR-0015
 * Hard Invariant 7: the gateway is faked at the fetch boundary only.
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { loadActiveSessionData } from '../../src/app/session-data-loader.ts';
import type { MatchedRoute } from '../../src/router/index.ts';
import type { RunefobleApp } from '../../src/runefoble-app.ts';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';
import { FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS } from '../support/app-data-service.fixtures.ts';
import { OWNER_BOARD_STATE, OWNER_SESSION_STATE } from '../support/owner-wire-fixtures.ts';

const ROUTE = { params: { campaignId: '4', sessionId: 'session-new' } } as unknown as MatchedRoute;
const CHRONICLE = [{ event_id: 'ev-1', kind: 'session_started', occurred_at: '2026-11-19T15:45:00Z', speaker: 'The Watcher', text: 'The session begins.', penalties: [] }];

function installSessionGateway(
  board: { status?: number; body?: unknown },
  runSession = true,
  session: { status?: number; body?: unknown } = { body: OWNER_SESSION_STATE },
): FakeGateway {
  return installFakeGateway({
    'GET /api/v1/boards/session-new': board,
    'GET /api/v1/sessions/session-new': session,
    'GET /api/v1/sessions/session-new/events': { body: CHRONICLE },
    'GET /api/v1/characters': { body: FALLBACK_CHARACTERS },
    'GET /api/v1/campaigns/4': { body: FALLBACK_CAMPAIGNS[0] },
    'GET /api/v1/campaigns/4/capabilities': { body: { manage: runSession, run_session: runSession, play: true, view: true } },
  });
}

function newHost(): RunefobleApp {
  return {
    characters: [], events: [], tokens: [{ id: 'stale', name: 'Stale', x: 0, y: 0 }], loadError: null,
    boardKind: 'board', sessionSeats: [], boardCols: 10, boardRows: 10, sessionTitle: 'Session', currentCampaign: null,
    campaignCapabilities: null, resolveActiveCharacter: () => null,
  } as unknown as RunefobleApp;
}

describe('Live session load without a board', () => {
  let gateway: FakeGateway;

  afterEach(() => gateway.restore());

  it('loads the feed and roster and marks the board as no_board when the board is 404', async () => {
    gateway = installSessionGateway({ status: 404, body: { detail: 'Board not found' } });
    const host = newHost();
    await loadActiveSessionData(host, ROUTE);
    assert.equal(host.loadError, null);
    assert.equal(host.boardKind, 'no_board');
    assert.deepEqual(host.tokens, []);
    assert.deepEqual(host.events.map((e) => e.text), ['The session begins.']);
    assert.equal(host.characters.length, FALLBACK_CHARACTERS.length);
    assert.equal(host.campaignCapabilities?.run_session, true);
  });

  it('keeps the error view when the board read is 503', async () => {
    gateway = installSessionGateway({ status: 503, body: { detail: 'Board service unavailable' } });
    const host = newHost();
    await loadActiveSessionData(host, ROUTE);
    assert.equal(host.loadError?.status, 503);
    assert.equal(host.loadError?.message, 'Board service unavailable');
  });

  it('marks a loaded board as board and copies its size', async () => {
    gateway = installSessionGateway({ body: OWNER_BOARD_STATE });
    const host = newHost();
    await loadActiveSessionData(host, ROUTE);
    assert.equal(host.loadError, null);
    assert.equal(host.boardKind, 'board');
    assert.equal(host.boardCols, OWNER_BOARD_STATE.cols);
    assert.ok(host.tokens.length >= 1);
  });

  it('shows the token cells of the board read, not the cells shown before it', async () => {
    gateway = installSessionGateway({ body: OWNER_BOARD_STATE });
    const host = newHost();
    host.tokens = [{ id: 'tok-valeros', name: 'Valeros', x: 0, y: 0 }];
    await loadActiveSessionData(host, ROUTE);
    const valeros = host.tokens.find((t) => t.id === 'tok-valeros');
    assert.deepEqual([valeros?.x, valeros?.y], [2, 3]);
  });

  it('reads the seated characters for a DM when the board is 404 (TASK-0922)', async () => {
    gateway = installSessionGateway({ status: 404, body: { detail: 'Board not found' } });
    const host = newHost();
    await loadActiveSessionData(host, ROUTE);
    assert.equal(host.loadError, null);
    assert.deepEqual(host.sessionSeats, [
      { characterId: 'char-valeros', characterName: 'Valeros of Korvosa' },
      { characterId: 'char-kyra', characterName: 'Kyra the Sun Maiden' },
    ]);
  });

  it('does not read the seats for a player, who has no set-up control', async () => {
    gateway = installSessionGateway({ status: 404, body: { detail: 'Board not found' } }, false, { status: 500, body: { detail: 'not read' } });
    const host = newHost();
    await loadActiveSessionData(host, ROUTE);
    assert.equal(host.loadError, null);
    assert.deepEqual(host.sessionSeats, []);
  });

  it('shows the error view when the DM seat read fails', async () => {
    gateway = installSessionGateway({ status: 404, body: { detail: 'Board not found' } }, true, { status: 503, body: { detail: 'Session service unavailable' } });
    const host = newHost();
    await loadActiveSessionData(host, ROUTE);
    assert.equal(host.loadError?.status, 503);
    assert.equal(host.loadError?.message, 'Session service unavailable');
  });
});
