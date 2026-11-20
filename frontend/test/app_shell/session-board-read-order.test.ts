/**
 * Board reads resolve in any order (TASK-0938).
 *
 * A route load reads the board, and a `board_ready` frame or a route change can start a second
 * read while the first is still out. The first read can answer last. Its tokens were read
 * before the newer read, so they must never replace the newer tokens.
 * Hard Invariant 7: the gateway is faked at the fetch boundary only.
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { loadActiveSessionData } from '../../src/app/session-data-loader.ts';
import type { MatchedRoute } from '../../src/router/index.ts';
import type { RunefobleApp } from '../../src/runefoble-app.ts';
import { FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS } from '../support/app-data-service.fixtures.ts';
import { OWNER_SESSION_STATE } from '../support/owner-wire-fixtures.ts';

const ROUTE = { params: { campaignId: '4', sessionId: 'session-new' } } as unknown as MatchedRoute;
const BOARD_PATH = '/api/v1/boards/session-new';

function boardBody(valerosX: number, valerosY: number) {
  return {
    board_id: '6d0c3b1e-2f4a-4c59-9a8e-1f2b3c4d5e6f', session_id: 'session-new', cols: 10, rows: 10,
    tokens: {
      'tok-valeros': {
        token_id: 'tok-valeros', name: 'Valeros the Bold', token_type: 'pc', x: valerosX, y: valerosY,
        hp: 24, is_friendly: true, vision_radius: 2, active_hazard: null, hazard_status: null, active_action: null,
      },
    },
    terrain_cells: {}, active_hazards: [], active_decals: [], fog_of_war_enabled: true, revealed_cells: [],
    background_asset_id: null, background_image_url: null,
  };
}

/**
 * Replaces fetch. Every board read waits until the test answers it, and the test answers in the
 * order it chooses. The other routes answer at once.
 */
function installOutOfOrderBoardReads() {
  const original = globalThis.fetch;
  /** The board reads in issue order. An answered read keeps its place. */
  const issued: Array<(body: unknown) => void> = [];
  const immediate: Record<string, unknown> = {
    '/api/v1/sessions/session-new': OWNER_SESSION_STATE,
    '/api/v1/sessions/session-new/events': [],
    '/api/v1/characters': FALLBACK_CHARACTERS,
    '/api/v1/campaigns/4': FALLBACK_CAMPAIGNS[0],
    '/api/v1/campaigns/4/capabilities': { manage: false, run_session: false, play: true, view: true },
  };
  globalThis.fetch = (async (input: string | URL | Request) => {
    const raw = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
    const path = new URL(raw, 'https://gateway.test').pathname;
    if (path === BOARD_PATH) {
      const body = await new Promise<unknown>((resolve) => issued.push(resolve));
      return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    const body = immediate[path];
    if (body === undefined) return new Response(JSON.stringify({ detail: `No fake route for ${path}` }), { status: 500 });
    return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }) as typeof fetch;
  return {
    /** Answers the board read with this issue number (0 is the first read). */
    answerBoardRead(index: number, body: unknown) {
      const resolve = issued[index];
      assert.ok(resolve, `board read ${index} must have been issued`);
      resolve(body);
    },
    restore() {
      globalThis.fetch = original;
    },
  };
}

function newHost(): RunefobleApp {
  return {
    characters: [], events: [], tokens: [], loadError: null,
    boardKind: 'loading', sessionSeats: [], boardCols: 10, boardRows: 10, sessionTitle: 'Session', currentCampaign: null,
    campaignCapabilities: null, resolveActiveCharacter: () => null, lobbyParticipants: [],
  } as unknown as RunefobleApp;
}

/** Lets the pending fetch promises settle, so a board read is pending before the test answers it. */
async function settle(): Promise<void> {
  for (let i = 0; i < 10; i += 1) await new Promise((resolve) => setImmediate(resolve));
}

describe('Board reads resolve in any order', () => {
  let reads: ReturnType<typeof installOutOfOrderBoardReads>;

  afterEach(() => reads.restore());

  it('a read issued earlier that answers last does not replace the newer board', async () => {
    reads = installOutOfOrderBoardReads();
    const host = newHost();

    const older = loadActiveSessionData(host, ROUTE);
    await settle();
    const newer = loadActiveSessionData(host, ROUTE);
    await settle();

    // The newer read sees the token moved to (3, 3). The older read still has (0, 0).
    reads.answerBoardRead(1, boardBody(3, 3));
    await newer;
    reads.answerBoardRead(0, boardBody(0, 0));
    await older;

    assert.equal(host.boardKind, 'board');
    assert.deepEqual(
      host.tokens.map((t) => [t.id, t.x, t.y]),
      [['tok-valeros', 3, 3]],
    );
  });

  it('the newest read still applies when it answers first', async () => {
    reads = installOutOfOrderBoardReads();
    const host = newHost();

    const older = loadActiveSessionData(host, ROUTE);
    await settle();
    const newer = loadActiveSessionData(host, ROUTE);
    await settle();

    reads.answerBoardRead(1, boardBody(3, 3));
    await newer;
    assert.deepEqual(host.tokens.map((t) => [t.x, t.y]), [[3, 3]]);

    reads.answerBoardRead(0, boardBody(0, 0));
    await older;
    assert.deepEqual(host.tokens.map((t) => [t.x, t.y]), [[3, 3]]);
  });
});
