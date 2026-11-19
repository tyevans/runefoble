/**
 * Board token updates replace the token list (TASK-0908, ADR-0004).
 *
 * `<runefoble-board>` sends tokens to the 3D view only when the `tokens` property gets a new
 * array. Each server message that moves or changes a token must put a new list with a new
 * token object on the host, and must leave the old list and token as they were.
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { executeRadialAction, handleBoardSocketMessage } from '../src/board-actions.ts';
import { PhysicsBridge } from '../src/physics_3d/physics_bridge.ts';
import type { BoardToken } from '../src/board-types.ts';

function makeHost() {
  const tokens = [{ id: 'valeros', name: 'Valeros', x: 1, y: 1 }, { id: 'kyra', name: 'Kyra', x: 4, y: 4 }] as BoardToken[];
  return {
    tokens,
    activeAoE: null,
    aoeAffectedTokenIds: [] as string[],
    aoeAffectedCells: [] as [number, number][],
    ws: null,
    terrainCells: [],
    ghostEngine: null,
    updates: 0,
    dispatchEvent: () => true,
    requestUpdate() { this.updates += 1; },
  };
}

describe('board token updates', () => {
  it('token_moved puts a new list and a new token on the host', () => {
    const host = makeHost();
    const [oldValeros, oldKyra] = host.tokens;
    const oldList = host.tokens;

    handleBoardSocketMessage(host, { action: 'token_moved', token_id: 'valeros', x: 3, y: 2 });

    assert.notEqual(host.tokens, oldList);
    assert.notEqual(host.tokens[0], oldValeros);
    assert.deepEqual([host.tokens[0].x, host.tokens[0].y], [3, 2]);
    assert.equal(host.tokens[1], oldKyra);
    assert.deepEqual([oldValeros.x, oldValeros.y], [1, 1]);
  });

  it('token_placed adds the server token to a new list, and keeps the old list as it was', () => {
    const host = makeHost();
    const oldList = host.tokens;

    handleBoardSocketMessage(host, {
      type: 'token_placed',
      session_id: 's-1',
      token: { token_id: 'sarah', name: 'Sarah', x: 0, y: 1, hp: 12, vision_radius: 3, active_action: null },
    });

    assert.notEqual(host.tokens, oldList);
    assert.equal(oldList.length, 2);
    assert.deepEqual(host.tokens[2], { id: 'sarah', name: 'Sarah', x: 0, y: 1, hp: 12, visionRadius: 3, activeAction: null });
  });

  it('token_placed for a token the host shows replaces that token', () => {
    const host = makeHost();

    handleBoardSocketMessage(host, { type: 'token_placed', token: { token_id: 'kyra', name: 'Kyra', x: 6, y: 6 } });

    assert.equal(host.tokens.length, 2);
    assert.deepEqual([host.tokens[1].x, host.tokens[1].y], [6, 6]);
  });

  it('token_placed without a whole token changes nothing', () => {
    const host = makeHost();
    const oldList = host.tokens;

    handleBoardSocketMessage(host, { type: 'token_placed', token: { token_id: 'sarah', name: 'Sarah' } });

    assert.equal(host.tokens, oldList);
  });

  it('the server token_action_executed broadcast puts a new token with the action on the host', () => {
    const host = makeHost();
    const oldValeros = host.tokens[0];

    handleBoardSocketMessage(host, { type: 'token_action_executed', action: 'attack', token_id: 'valeros' });

    assert.notEqual(host.tokens[0], oldValeros);
    assert.equal(host.tokens[0].activeAction, 'attack');
    assert.equal(oldValeros.activeAction, undefined);
  });

  it('a radial action puts a new token with the action on the host', () => {
    const host = makeHost();
    const oldValeros = host.tokens[0];

    executeRadialAction(host, 'dash', 'valeros');

    assert.notEqual(host.tokens[0], oldValeros);
    assert.equal(host.tokens[0].activeAction, 'dash');
    assert.equal(oldValeros.activeAction, undefined);
  });

  it('a knockback puts a new list and a new token on the host', () => {
    const host = makeHost();
    const oldList = host.tokens;
    const oldValeros = host.tokens[0];
    const bridge = new PhysicsBridge(host, null);

    assert.equal(bridge.handleWebSocketMessage({ type: 'token_knockback', token_id: 'valeros', from_x: 1, from_y: 1, to_x: 2, to_y: 1 }), true);

    assert.notEqual(host.tokens, oldList);
    assert.deepEqual([host.tokens[0].x, host.tokens[0].y], [2, 1]);
    assert.deepEqual([oldValeros.x, oldValeros.y], [1, 1]);
  });
});
