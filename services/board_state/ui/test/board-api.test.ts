/**
 * Board UI public-route client tests (TASK-0563).
 * Fetch is stubbed at the browser boundary only. Assertions check the
 * request method, URL, and body that the UI sends to the public routes.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  BoardApiError,
  boardSocketUrl,
  buildConfirmMoveMessage,
  postSwitchMap,
  postTrap,
  type FetchLike,
} from '../src/board-api.ts';

interface Captured { url: string; init: RequestInit | undefined }

function stubFetch(status: number, body: unknown): { fetchImpl: FetchLike; calls: Captured[] } {
  const calls: Captured[] = [];
  const fetchImpl: FetchLike = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  };
  return { fetchImpl, calls };
}

describe('postTrap', () => {
  it('posts the trap draft to the public traps route with campaign_id', async () => {
    const { fetchImpl, calls } = stubFetch(201, { trap_id: 'trap-1', name: 'Pit', is_armed: true });
    const trap = await postTrap('board-42', {
      name: 'Spiked Pit', trapType: 'pit_trap', x: 4, y: 5, triggerType: 'step',
      proximityRadius: 1, dcDetection: 16, damageDice: '2d10', isSecret: true,
    }, { campaignId: 'camp-7', fetchImpl });

    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, '/api/v1/boards/board-42/traps?campaign_id=camp-7');
    assert.equal(calls[0].init?.method, 'POST');
    assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
      name: 'Spiked Pit', trap_type: 'pit_trap', x: 4, y: 5, trigger_type: 'step',
      proximity_radius: 1, dc_detection: 16, damage_dice: '2d10', is_secret: true,
    });
    assert.equal(trap.trap_id, 'trap-1');
  });

  it('omits campaign_id when no campaign is given', async () => {
    const { fetchImpl, calls } = stubFetch(201, { trap_id: 'trap-2' });
    await postTrap('board-42', {
      name: 'Tripwire', trapType: 'tripwire', x: 1, y: 1, triggerType: 'touch',
      proximityRadius: 1, dcDetection: 12, damageDice: '1d6', isSecret: true,
    }, { fetchImpl });
    assert.equal(calls[0].url, '/api/v1/boards/board-42/traps');
  });

  it('throws BoardApiError with the server status on a rejected request', async () => {
    const { fetchImpl } = stubFetch(403, { detail: 'Forbidden: DM permissions required to create secret traps' });
    await assert.rejects(
      postTrap('board-42', {
        name: 'Pit', trapType: 'pit_trap', x: 0, y: 0, triggerType: 'step',
        proximityRadius: 1, dcDetection: 15, damageDice: '2d10', isSecret: true,
      }, { fetchImpl }),
      (err: unknown) => err instanceof BoardApiError && err.status === 403 && err.detail.includes('DM permissions'),
    );
  });
});

describe('postSwitchMap', () => {
  it('posts the map draft to the public switch-map route', async () => {
    const { fetchImpl, calls } = stubFetch(200, {
      board_id: 'board-42', new_map_id: 'dungeon_lvl2', cols: 20, rows: 20,
      teleported_tokens: { valeros: [10, 15] }, status: 'switched',
    });
    const resp = await postSwitchMap('board-42', {
      newMapId: 'dungeon_lvl2', cols: 20, rows: 20, backgroundImageUrl: '',
      tokenTeleports: { valeros: [10, 15] },
    }, { campaignId: 'camp-7', fetchImpl });

    assert.equal(calls[0].url, '/api/v1/boards/board-42/switch-map?campaign_id=camp-7');
    assert.equal(calls[0].init?.method, 'POST');
    assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
      new_map_id: 'dungeon_lvl2', cols: 20, rows: 20, background_image_url: null,
      token_teleports: { valeros: [10, 15] },
    });
    assert.equal(resp.new_map_id, 'dungeon_lvl2');
    assert.deepEqual(resp.teleported_tokens, { valeros: [10, 15] });
  });

  it('throws BoardApiError when the server refuses the switch', async () => {
    const { fetchImpl } = stubFetch(403, { detail: 'Forbidden' });
    await assert.rejects(
      postSwitchMap('board-42', {
        newMapId: 'x', cols: 8, rows: 8, backgroundImageUrl: '', tokenTeleports: {},
      }, { fetchImpl }),
      (err: unknown) => err instanceof BoardApiError && err.status === 403,
    );
  });
});

describe('board socket contract', () => {
  it('builds the board socket URL on the board service path', () => {
    assert.equal(boardSocketUrl('https:', 'runefoble.local', 'sess-1'), 'wss://runefoble.local/ws/boards/sess-1');
    assert.equal(boardSocketUrl('http:', 'localhost:8000', 'sess-1'), 'ws://localhost:8000/ws/boards/sess-1');
  });

  it('maps a token move to the confirm_move action with snake_case fields', () => {
    assert.deepEqual(buildConfirmMoveMessage({ tokenId: 'valeros', toX: 3, toY: 4 }), {
      action: 'confirm_move', token_id: 'valeros', to_x: 3, to_y: 4, initiated_by: 'player',
    });
  });
});
