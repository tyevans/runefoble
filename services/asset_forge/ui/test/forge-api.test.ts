/**
 * Unit tests for the Asset Forge HTTP client.
 * TASK-0613: Asset Forge and Print Forge Components Call Forge API and Show Results.
 * TASK-0812: Every forge call sends the shared bearer.
 * TASK-0758: The calls run over the shared transport. Failures are `HttpError`.
 *
 * The calls go to a real HTTP server on the loopback interface. Nothing replaces `fetch`.
 * Requests and replies use the public forge route contracts from services/asset_forge.
 */

import { after, before, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import type { AddressInfo } from 'node:net';

import { HttpError, type AuthSource, type RequestOptions } from '@runefoble/ui-core';
import { startLoopbackUpstream, type LoopbackUpstream } from '@runefoble/ui-core/testing/loopback-upstream';
import {
  exportPrintPdf,
  exportStandees,
  exportStlToken,
  forgeBattlemap,
  forgeFailureMessage,
  forgeToken,
  placeBoardToken,
} from '../src/forge-api.ts';

const TEST_TOKEN = 'test-access-token';
const CAMPAIGN = '6f1d7c2e-0000-4000-8000-000000000001';
const signedIn: AuthSource = { authHeaders: async () => ({ Authorization: `Bearer ${TEST_TOKEN}` }) };
const anonymous: AuthSource = { authHeaders: async () => ({}) };

let upstream: LoopbackUpstream;
let opts: RequestOptions;

before(async () => {
  upstream = await startLoopbackUpstream();
});

after(() => upstream.close());

beforeEach(() => {
  upstream.reset();
  opts = { apiBase: upstream.url, auth: signedIn };
});

/** The one request that the upstream received, with its JSON body parsed. */
function onlyCall() {
  assert.equal(upstream.requests.length, 1);
  const req = upstream.requests[0];
  return { method: req.method, path: req.path, headers: req.headers, body: req.body ? JSON.parse(req.body) : undefined };
}

async function rejection(promise: Promise<unknown>): Promise<HttpError> {
  try {
    await promise;
  } catch (err) {
    assert.ok(err instanceof HttpError, `expected HttpError, got ${String(err)}`);
    return err;
  }
  throw new assert.AssertionError({ message: 'The call resolved. It must reject.' });
}

const BATTLEMAP_RESPONSE = {
  asset_id: 'map-abc123def456',
  image_url: '/api/v1/assets/map-abc123def456',
  download_url: '/api/v1/assets/map-abc123def456',
  width_cells: 20,
  height_cells: 20,
  cell_size_px: 64,
  theme: 'dwarven_forge',
  wall_segments: [{ x1: 0, y1: 0, x2: 1, y2: 0 }, { x1: 1, y1: 0, x2: 1, y2: 1 }],
  hazard_cells: [{ x: 3, y: 4, hazard_type: 'lava', terrain_type: 'difficult' }],
  doors: [],
  status: 'forged',
};

const SILO_DOWN = 'Silo asset storage is unavailable. The asset was not stored.';

describe('forgeBattlemap (TASK-0613)', () => {
  it('posts the prompt and grid size under the API base and maps the forged asset', async () => {
    upstream.reply(200, BATTLEMAP_RESPONSE);

    const map = await forgeBattlemap(
      { prompt: 'Lava forge', campaignId: CAMPAIGN, widthCells: 20, heightCells: 20 },
      opts,
    );

    const call = onlyCall();
    assert.equal(call.method, 'POST');
    assert.equal(call.path, '/api/v1/forge/battlemap');
    assert.equal(call.headers['content-type'], 'application/json');
    assert.deepEqual(call.body, {
      prompt: 'Lava forge',
      campaign_id: CAMPAIGN,
      width_cells: 20,
      height_cells: 20,
    });
    assert.deepEqual(map, {
      asset_id: 'map-abc123def456',
      image_url: '/api/v1/assets/map-abc123def456',
      theme: 'dwarven_forge',
      width_cells: 20,
      height_cells: 20,
      wall_count: 2,
      hazard_count: 1,
    });
  });

  it('rejects with HttpError carrying the 503 detail when Silo is unavailable', async () => {
    upstream.reply(503, { detail: SILO_DOWN });

    const err = await rejection(forgeBattlemap({ prompt: 'Crypt', widthCells: 10, heightCells: 10, campaignId: CAMPAIGN }, opts));

    assert.equal(err.status, 503);
    assert.equal(forgeFailureMessage(err), SILO_DOWN);
  });

  it('joins FastAPI validation messages from a 422 body', async () => {
    upstream.reply(422, {
      detail: [
        { loc: ['body', 'prompt'], msg: 'String should have at least 3 characters', type: 'string_too_short' },
        { loc: ['body', 'width_cells'], msg: 'Input should be less than or equal to 50', type: 'less_than_equal' },
      ],
    });

    const err = await rejection(forgeBattlemap({ prompt: 'x', widthCells: 99, heightCells: 10, campaignId: CAMPAIGN }, opts));

    assert.equal(err.status, 422);
    assert.equal(
      forgeFailureMessage(err),
      'String should have at least 3 characters; Input should be less than or equal to 50',
    );
  });

  it('reports the HTTP status when the error body is not JSON', async () => {
    upstream.reply(502, '<html>Bad Gateway</html>');

    const err = await rejection(forgeBattlemap({ prompt: 'Crypt', widthCells: 10, heightCells: 10, campaignId: CAMPAIGN }, opts));

    assert.equal(err.status, 502);
    assert.match(forgeFailureMessage(err), /status 502/);
  });

  it('rejects with the network error instead of reporting success', async () => {
    const closed = createServer();
    await new Promise<void>((resolve) => closed.listen(0, '127.0.0.1', resolve));
    const deadBase = `http://127.0.0.1:${(closed.address() as AddressInfo).port}`;
    await new Promise<void>((resolve) => closed.close(() => resolve()));

    await assert.rejects(
      forgeBattlemap({ prompt: 'Crypt', widthCells: 10, heightCells: 10, campaignId: CAMPAIGN }, { apiBase: deadBase, auth: signedIn }),
      (err: unknown) => {
        assert.ok(err instanceof TypeError);
        assert.match(forgeFailureMessage(err), /^Network error: /);
        return true;
      },
    );
  });
});

describe('forge bearer and refusal text (TASK-0812, TASK-0758)', () => {
  const forgeCalls: Array<[string, (o: RequestOptions) => Promise<unknown>]> = [
    ['forgeBattlemap', (o) => forgeBattlemap({ prompt: 'Crypt', widthCells: 10, heightCells: 10, campaignId: CAMPAIGN }, o)],
    ['forgeToken', (o) => forgeToken({ prompt: 'Paladin', tokenName: 'Thorin', tokenType: 'pc', campaignId: CAMPAIGN }, o)],
    ['exportPrintPdf', (o) => exportPrintPdf({ title: 'Crypt', widthCells: 16, heightCells: 16, pageSize: 'letter', campaignId: CAMPAIGN }, o)],
    ['exportStandees', (o) => exportStandees({ sheetTitle: 'Standees', standees: [], pageSize: 'a4', campaignId: CAMPAIGN }, o)],
    ['exportStlToken', (o) => exportStlToken({ diameterMm: 28, conditionLabel: 'Poisoned', numSlots: 4, campaignId: CAMPAIGN }, o)],
    ['placeBoardToken', (o) => placeBoardToken({ sessionId: 's', name: 'n', tokenType: 'pc', x: 1, y: 1 }, o)],
  ];

  for (const [name, call] of forgeCalls) {
    it(`${name} sends the shared bearer as Authorization`, async () => {
      upstream.reply(200, minimalResponseFor(name));

      await call(opts);

      const { headers } = onlyCall();
      assert.equal(headers.authorization, `Bearer ${TEST_TOKEN}`);
      assert.equal('x-user-id' in headers, false);
    });

    it(`${name} sends no Authorization header when no token exists`, async () => {
      upstream.reply(200, minimalResponseFor(name));

      await call({ apiBase: upstream.url, auth: anonymous });

      assert.equal('authorization' in onlyCall().headers, false);
    });

    it(`${name} shows a sign-in message on 401`, async () => {
      upstream.reply(401, { detail: 'Not authenticated' });

      const err = await rejection(call(opts));

      assert.equal(err.status, 401);
      assert.match(forgeFailureMessage(err), /Sign in/);
    });

    it(`${name} shows a permission message on 403`, async () => {
      upstream.reply(403, { detail: 'Forbidden' });

      const err = await rejection(call(opts));

      assert.equal(err.status, 403);
      assert.match(forgeFailureMessage(err), /permission/);
    });
  }
});

function minimalResponseFor(name: string): unknown {
  switch (name) {
    case 'forgeBattlemap':
      return BATTLEMAP_RESPONSE;
    case 'forgeToken':
      return { asset_id: 'tok-1', image_url: '/api/v1/assets/tok-1', token_name: 'Thorin', token_type: 'pc', size_px: 256 };
    case 'exportPrintPdf':
      return { asset_id: 'pdf-1', download_url: '/api/v1/assets/pdf-1', total_pages: 1, page_size: 'letter' };
    case 'exportStandees':
      return { asset_id: 'std-1', download_url: '/api/v1/assets/std-1', standee_count: 0, pages: 1 };
    case 'exportStlToken':
      return { asset_id: 'stl-1', download_url: '/api/v1/assets/stl-1', facet_count: 1, is_watertight: true };
    default:
      return { token_id: 't', name: 'n', token_type: 'pc', x: 1, y: 1 };
  }
}

describe('forgeToken (TASK-0613)', () => {
  it('posts the token prompt and identity and maps the forged portrait', async () => {
    upstream.reply(200, {
      asset_id: 'tok-0123456789ab',
      image_url: '/api/v1/assets/tok-0123456789ab',
      download_url: '/api/v1/assets/tok-0123456789ab',
      token_name: 'Thorin Ironbreaker',
      token_type: 'pc',
      crop_style: 'circular',
      size_px: 256,
      has_transparency: true,
      status: 'forged',
    });

    const token = await forgeToken(
      { prompt: 'Dwarven paladin', tokenName: 'Thorin Ironbreaker', tokenType: 'pc', campaignId: CAMPAIGN },
      opts,
    );

    const call = onlyCall();
    assert.equal(call.path, '/api/v1/forge/token');
    assert.deepEqual(call.body, { prompt: 'Dwarven paladin', token_name: 'Thorin Ironbreaker', token_type: 'pc', campaign_id: CAMPAIGN });
    assert.deepEqual(token, {
      asset_id: 'tok-0123456789ab',
      image_url: '/api/v1/assets/tok-0123456789ab',
      token_name: 'Thorin Ironbreaker',
      token_type: 'pc',
      size_px: 256,
    });
  });
});

describe('print forge exports (TASK-0613)', () => {
  it('requests the PDF as JSON so the returned download URL can be offered', async () => {
    upstream.reply(200, {
      asset_id: 'pdf-aaaaaaaaaaaa',
      download_url: '/api/v1/assets/pdf-aaaaaaaaaaaa',
      total_pages: 9,
      rows: 3,
      cols: 3,
      page_size: 'letter',
      grid_calibration: '1-inch (72pt)',
      status: 'forged',
    });

    const result = await exportPrintPdf(
      { title: 'Crypt', widthCells: 16, heightCells: 16, pageSize: 'letter', campaignId: CAMPAIGN },
      opts,
    );

    const call = onlyCall();
    assert.equal(call.path, '/api/v1/forge/print-pdf');
    assert.deepEqual(call.body, { title: 'Crypt', width_cells: 16, height_cells: 16, page_size: 'letter', format: 'json', campaign_id: CAMPAIGN });
    assert.equal(result.asset_id, 'pdf-aaaaaaaaaaaa');
    assert.equal(result.download_url, '/api/v1/assets/pdf-aaaaaaaaaaaa');
  });

  it('posts standees and returns the downloadable sheet', async () => {
    upstream.reply(200, {
      asset_id: 'std-bbbbbbbbbbbb',
      download_url: '/api/v1/assets/std-bbbbbbbbbbbb',
      standee_count: 1,
      pages: 1,
      page_size: 'a4',
      status: 'forged',
    });
    const standees = [{ name: 'Valeros Fighter', type: 'pc', hp: 24, color: '#2a9d8f' }];

    const result = await exportStandees(
      { sheetTitle: 'Valeros Fighter Standees', standees, pageSize: 'a4', campaignId: CAMPAIGN },
      opts,
    );

    const call = onlyCall();
    assert.equal(call.path, '/api/v1/forge/standees');
    assert.deepEqual(call.body, { sheet_title: 'Valeros Fighter Standees', standees, page_size: 'a4', format: 'json', campaign_id: CAMPAIGN });
    assert.equal(result.download_url, '/api/v1/assets/std-bbbbbbbbbbbb');
  });

  it('posts an STL token request and returns the downloadable mesh', async () => {
    upstream.reply(200, {
      asset_id: 'stl-cccccccccccc',
      download_url: '/api/v1/assets/stl-cccccccccccc',
      diameter_mm: 28,
      height_mm: 3.5,
      facet_count: 512,
      is_watertight: true,
      condition_label: 'Poisoned',
      status: 'forged',
    });

    const result = await exportStlToken({ diameterMm: 28, conditionLabel: 'Poisoned', numSlots: 4, campaignId: CAMPAIGN }, opts);

    const call = onlyCall();
    assert.equal(call.path, '/api/v1/forge/stl-token');
    assert.deepEqual(call.body, { diameter_mm: 28, condition_label: 'Poisoned', num_slots: 4, format: 'json', campaign_id: CAMPAIGN });
    assert.equal(result.download_url, '/api/v1/assets/stl-cccccccccccc');
  });

  it('shows the 503 detail from the print route', async () => {
    upstream.reply(503, { detail: SILO_DOWN });

    const err = await rejection(
      exportStlToken({ diameterMm: 28, conditionLabel: 'Poisoned', numSlots: 4, campaignId: CAMPAIGN }, opts),
    );

    assert.equal(err.status, 503);
    assert.equal(forgeFailureMessage(err), SILO_DOWN);
  });
});

describe('placeBoardToken', () => {
  it('posts the token to the session board route and maps the placed token', async () => {
    upstream.reply(200, {
      token_id: 'tok-1',
      name: 'Thorin Ironbreaker',
      token_type: 'pc',
      x: 4,
      y: 7,
      hp: null,
      is_friendly: true,
      vision_radius: 2,
    });

    const result = await placeBoardToken(
      { sessionId: 'session-42', name: 'Thorin Ironbreaker', tokenType: 'pc', x: 4, y: 7 },
      opts,
    );

    const call = onlyCall();
    assert.equal(call.method, 'POST');
    assert.equal(call.path, '/api/v1/boards/session-42/tokens');
    assert.deepEqual(call.body, { name: 'Thorin Ironbreaker', token_type: 'pc', x: 4, y: 7 });
    assert.deepEqual(result, { token_id: 'tok-1', name: 'Thorin Ironbreaker', token_type: 'pc', x: 4, y: 7 });
  });

  it('encodes the session id in the route path', async () => {
    upstream.reply(200, { token_id: 't', name: 'n', token_type: 'npc', x: 0, y: 0 });

    await placeBoardToken({ sessionId: 'a/b c', name: 'n', tokenType: 'npc', x: 0, y: 0 }, opts);

    assert.equal(onlyCall().path, '/api/v1/boards/a%2Fb%20c/tokens');
  });

  it('shows the board detail on 400', async () => {
    upstream.reply(400, { detail: 'Cell is occupied by another token.' });

    const err = await rejection(placeBoardToken({ sessionId: 's', name: 'n', tokenType: 'pc', x: 1, y: 1 }, opts));

    assert.equal(err.status, 400);
    assert.equal(forgeFailureMessage(err), 'Cell is occupied by another token.');
  });
});

describe('forgeFailureMessage', () => {
  it('shows the message of a local precondition error', () => {
    assert.equal(forgeFailureMessage(new Error('Forge a token before placing it.')), 'Forge a token before placing it.');
  });
});
