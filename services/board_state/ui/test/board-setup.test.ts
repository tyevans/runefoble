/**
 * DM battlemap set-up flow tests (TASK-0922, TASK-0928).
 * Fetch is stubbed at the browser boundary only. Assertions check the requests that the flow
 * sends to the public gateway routes and the result that it returns.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import type { FetchLike } from '@runefoble/ui-core';
import { setUpSessionBoard, startCells } from '../src/board-setup.ts';

interface Reply { status: number; body: unknown }

function scriptedFetch(replies: Reply[]): { fetchImpl: FetchLike; paths: string[] } {
  const paths: string[] = [];
  const fetchImpl: FetchLike = async (url) => {
    paths.push(url);
    const reply = replies[paths.length - 1];
    if (!reply) throw new Error(`Unexpected request ${url}`);
    return new Response(JSON.stringify(reply.body), { status: reply.status, headers: { 'Content-Type': 'application/json' } });
  };
  return { fetchImpl, paths };
}

const SEATS = [
  { characterId: 'c-1', characterName: 'Valeros' },
  { characterId: 'c-2', characterName: 'Sarah' },
];

describe('startCells', () => {
  it('returns free cells in row order from the top-left cell', () => {
    assert.deepEqual(startCells(3, 2, 2), [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 0, y: 1 }]);
  });

  it('skips an occupied cell', () => {
    assert.deepEqual(startCells(2, 3, 3, [{ x: 0, y: 0 }]), [{ x: 1, y: 0 }, { x: 2, y: 0 }]);
  });

  it('refuses a party larger than the free cells', () => {
    assert.throws(() => startCells(5, 2, 2), RangeError);
  });
});

describe('setUpSessionBoard', () => {
  it('sends one set-up call with the grid and one party token for each seat at free start cells', async () => {
    const { fetchImpl, paths } = scriptedFetch([{ status: 200, body: { board: {}, tokens: [{}, {}] } }]);
    const bodies: unknown[] = [];
    const recording: FetchLike = async (url, init) => {
      bodies.push(JSON.parse(String(init?.body)));
      return fetchImpl(url, init);
    };
    const result = await setUpSessionBoard(
      { campaignId: 'camp', sessionId: 'sess', seats: SEATS, cols: 1, rows: 5 },
      { fetchImpl: recording },
    );
    assert.deepEqual(result, { ok: true, placed: 2 });
    assert.deepEqual(paths, ['/api/v1/boards']);
    assert.deepEqual(bodies, [{
      campaign_id: 'camp',
      session_id: 'sess',
      cols: 1,
      rows: 5,
      tokens: [
        { name: 'Valeros', token_type: 'pc', x: 0, y: 0, character_id: 'c-1' },
        { name: 'Sarah', token_type: 'pc', x: 0, y: 1, character_id: 'c-2' },
      ],
    }]);
  });

  it('reports a refused token after the board exists with the gateway message', async () => {
    const { fetchImpl } = scriptedFetch([{
      status: 403,
      body: { detail: 'Valeros: Forbidden: placing a character token requires character.edit', token: 'Valeros', board_created: true },
    }]);
    const result = await setUpSessionBoard({ campaignId: 'camp', sessionId: 'sess', seats: SEATS }, { fetchImpl });
    assert.deepEqual(result, {
      ok: false,
      boardCreated: true,
      message: 'Valeros: Forbidden: placing a character token requires character.edit',
    });
  });

  it('reports a refused board create with the owner message', async () => {
    const { fetchImpl } = scriptedFetch([{ status: 409, body: { detail: 'A board exists for session sess' } }]);
    const result = await setUpSessionBoard({ campaignId: 'camp', sessionId: 'sess', seats: SEATS }, { fetchImpl });
    assert.deepEqual(result, { ok: false, boardCreated: false, message: 'A board exists for session sess' });
  });

  it('sends nothing when the grid has too few start cells for the party', async () => {
    const { fetchImpl, paths } = scriptedFetch([]);
    const result = await setUpSessionBoard(
      { campaignId: 'camp', sessionId: 'sess', seats: SEATS, cols: 1, rows: 1 },
      { fetchImpl },
    );
    assert.equal(result.ok, false);
    assert.equal(result.ok === false && result.boardCreated, false);
    assert.deepEqual(paths, []);
  });
});
