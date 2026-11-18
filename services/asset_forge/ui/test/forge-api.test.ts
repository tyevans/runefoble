/**
 * Unit tests for the Asset Forge HTTP client.
 * TASK-0613: Asset Forge and Print Forge Components Call Forge API and Show Results.
 * TASK-0812: Every forge call sends the shared bearer and maps 401 and 403 to a typed error.
 *
 * The network boundary (fetch) is replaced with a recording stub. Requests and
 * responses use the public forge route contracts from services/asset_forge.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  ForgeApiError,
  ForgeAuthError,
  exportPrintPdf,
  exportStandees,
  exportStlToken,
  forgeBattlemap,
  forgeToken,
  placeBoardToken,
  type AuthHeaders,
} from '../src/forge-api.ts';

interface RecordedCall {
  url: string;
  method: string;
  headers: Record<string, string>;
  body: unknown;
}

const TEST_TOKEN = 'test-access-token';
const auth: AuthHeaders = async () => ({ Authorization: `Bearer ${TEST_TOKEN}` });
const anonymous: AuthHeaders = async () => ({});

function stubFetch(respond: () => Response | Promise<Response>) {
  const calls: RecordedCall[] = [];
  const fetchImpl = async (input: string | URL | Request, init?: RequestInit) => {
    const bodyText = typeof init?.body === 'string' ? init.body : undefined;
    calls.push({
      url: String(input),
      method: init?.method ?? 'GET',
      headers: { ...(init?.headers as Record<string, string>) },
      body: bodyText === undefined ? undefined : JSON.parse(bodyText),
    });
    return respond();
  };
  return { calls, fetchImpl: fetchImpl as typeof fetch };
}

function jsonResponse(status: number, payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const BATTLEMAP_RESPONSE = {
  asset_id: 'map-abc123def456',
  image_url: 'https://silo.example/battlemaps/map-abc123def456.png',
  download_url: 'https://silo.example/battlemaps/map-abc123def456.png',
  width_cells: 20,
  height_cells: 20,
  cell_size_px: 64,
  theme: 'dwarven_forge',
  wall_segments: [{ x1: 0, y1: 0, x2: 1, y2: 0 }, { x1: 1, y1: 0, x2: 1, y2: 1 }],
  hazard_cells: [{ x: 3, y: 4, hazard_type: 'lava', terrain_type: 'difficult' }],
  doors: [],
  status: 'forged',
};

describe('forgeBattlemap (TASK-0613)', () => {
  it('posts the prompt and grid size to the battlemap route and maps the forged asset', async () => {
    const { calls, fetchImpl } = stubFetch(() => jsonResponse(200, BATTLEMAP_RESPONSE));

    const map = await forgeBattlemap(
      '',
      { prompt: 'Lava forge', campaignId: '6f1d7c2e-0000-4000-8000-000000000001', widthCells: 20, heightCells: 20 },
      auth,
      fetchImpl,
    );

    assert.equal(calls.length, 1);
    assert.equal(calls[0].method, 'POST');
    assert.equal(calls[0].url, '/api/v1/forge/battlemap');
    assert.deepEqual(calls[0].body, {
      prompt: 'Lava forge',
      campaign_id: '6f1d7c2e-0000-4000-8000-000000000001',
      width_cells: 20,
      height_cells: 20,
    });
    assert.deepEqual(map, {
      asset_id: 'map-abc123def456',
      image_url: 'https://silo.example/battlemaps/map-abc123def456.png',
      theme: 'dwarven_forge',
      width_cells: 20,
      height_cells: 20,
      wall_count: 2,
      hazard_count: 1,
    });
  });

  it('prefixes the route with the configured base URL', async () => {
    const { calls, fetchImpl } = stubFetch(() => jsonResponse(200, BATTLEMAP_RESPONSE));

    await forgeBattlemap(
      'https://gateway.example',
      { prompt: 'Crypt', widthCells: 10, heightCells: 10 },
      auth,
      fetchImpl,
    );

    assert.equal(calls[0].url, 'https://gateway.example/api/v1/forge/battlemap');
  });

  it('omits campaign_id when no campaign is set', async () => {
    const { calls, fetchImpl } = stubFetch(() => jsonResponse(200, BATTLEMAP_RESPONSE));

    await forgeBattlemap('', { prompt: 'Crypt', campaignId: '', widthCells: 10, heightCells: 10 }, auth, fetchImpl);

    assert.equal('campaign_id' in (calls[0].body as Record<string, unknown>), false);
  });

  it('throws ForgeApiError carrying the 503 detail when Silo is unavailable', async () => {
    const detail = 'Silo asset storage is unavailable. The asset was not stored.';
    const { fetchImpl } = stubFetch(() => jsonResponse(503, { detail }));

    await assert.rejects(
      forgeBattlemap('', { prompt: 'Crypt', widthCells: 10, heightCells: 10 }, auth, fetchImpl),
      (err: unknown) => {
        assert.ok(err instanceof ForgeApiError);
        assert.equal(err.status, 503);
        assert.equal(err.message, detail);
        return true;
      },
    );
  });

  it('joins FastAPI validation messages from a 422 body', async () => {
    const { fetchImpl } = stubFetch(() =>
      jsonResponse(422, {
        detail: [
          { loc: ['body', 'prompt'], msg: 'String should have at least 3 characters', type: 'string_too_short' },
          { loc: ['body', 'width_cells'], msg: 'Input should be less than or equal to 50', type: 'less_than_equal' },
        ],
      }),
    );

    await assert.rejects(
      forgeBattlemap('', { prompt: 'x', widthCells: 99, heightCells: 10 }, auth, fetchImpl),
      (err: unknown) => {
        assert.ok(err instanceof ForgeApiError);
        assert.equal(err.status, 422);
        assert.equal(
          err.message,
          'String should have at least 3 characters; Input should be less than or equal to 50',
        );
        return true;
      },
    );
  });

  it('reports the HTTP status when the error body is not JSON', async () => {
    const { fetchImpl } = stubFetch(() => new Response('<html>Bad Gateway</html>', { status: 502 }));

    await assert.rejects(
      forgeBattlemap('', { prompt: 'Crypt', widthCells: 10, heightCells: 10 }, auth, fetchImpl),
      (err: unknown) => {
        assert.ok(err instanceof ForgeApiError);
        assert.equal(err.status, 502);
        assert.match(err.message, /HTTP 502/);
        return true;
      },
    );
  });

  it('propagates network failures instead of reporting success', async () => {
    const { fetchImpl } = stubFetch(() => {
      throw new TypeError('fetch failed');
    });

    await assert.rejects(
      forgeBattlemap('', { prompt: 'Crypt', widthCells: 10, heightCells: 10 }, auth, fetchImpl),
      TypeError,
    );
  });
});

describe('forge bearer and auth errors (TASK-0812)', () => {
  const forgeCalls: Array<[string, (fetchImpl: typeof fetch, authHeaders: AuthHeaders) => Promise<unknown>]> = [
    ['forgeBattlemap', (f, a) => forgeBattlemap('', { prompt: 'Crypt', widthCells: 10, heightCells: 10 }, a, f)],
    [
      'forgeToken',
      (f, a) => forgeToken('', { prompt: 'Paladin', tokenName: 'Thorin', tokenType: 'pc' }, a, f),
    ],
    [
      'exportPrintPdf',
      (f, a) =>
        exportPrintPdf('', { title: 'Crypt', widthCells: 16, heightCells: 16, pageSize: 'letter' }, a, f),
    ],
    [
      'exportStandees',
      (f, a) =>
        exportStandees('', { sheetTitle: 'Standees', standees: [], pageSize: 'a4' }, a, f),
    ],
    [
      'exportStlToken',
      (f, a) => exportStlToken('', { diameterMm: 28, conditionLabel: 'Poisoned', numSlots: 4 }, a, f),
    ],
    [
      'placeBoardToken',
      (f, a) => placeBoardToken('', { sessionId: 's', name: 'n', tokenType: 'pc', x: 1, y: 1 }, a, f),
    ],
  ];

  for (const [name, call] of forgeCalls) {
    it(`${name} sends the shared bearer as Authorization`, async () => {
      const { calls, fetchImpl } = stubFetch(() => jsonResponse(200, minimalResponseFor(name)));

      await call(fetchImpl, auth);

      assert.equal(calls.length, 1);
      assert.equal(calls[0].headers.Authorization, `Bearer ${TEST_TOKEN}`);
      assert.equal('x-user-id' in calls[0].headers, false);
    });

    it(`${name} sends no Authorization header when no token exists`, async () => {
      const { calls, fetchImpl } = stubFetch(() => jsonResponse(200, minimalResponseFor(name)));

      await call(fetchImpl, anonymous);

      assert.equal('Authorization' in calls[0].headers, false);
    });

    it(`${name} throws ForgeAuthError with a sign-in message on 401`, async () => {
      const { fetchImpl } = stubFetch(() => jsonResponse(401, { detail: 'Not authenticated' }));

      await assert.rejects(call(fetchImpl, auth), (err: unknown) => {
        assert.ok(err instanceof ForgeAuthError);
        assert.equal(err.status, 401);
        assert.match(err.message, /Sign in/);
        return true;
      });
    });

    it(`${name} throws ForgeAuthError with a permission message on 403`, async () => {
      const { fetchImpl } = stubFetch(() => jsonResponse(403, { detail: 'Forbidden' }));

      await assert.rejects(call(fetchImpl, auth), (err: unknown) => {
        assert.ok(err instanceof ForgeAuthError);
        assert.equal(err.status, 403);
        assert.match(err.message, /permission/);
        return true;
      });
    });
  }
});

function minimalResponseFor(name: string): unknown {
  switch (name) {
    case 'forgeBattlemap':
      return BATTLEMAP_RESPONSE;
    case 'forgeToken':
      return {
        asset_id: 'tok-1',
        image_url: 'https://silo.example/tokens/tok-1.png',
        token_name: 'Thorin',
        token_type: 'pc',
        size_px: 256,
      };
    case 'exportPrintPdf':
      return { asset_id: 'pdf-1', download_url: 'https://silo.example/pdf-1.pdf', total_pages: 1, page_size: 'letter' };
    case 'exportStandees':
      return { asset_id: 'std-1', download_url: 'https://silo.example/std-1.pdf', standee_count: 0, pages: 1 };
    case 'exportStlToken':
      return { asset_id: 'stl-1', download_url: 'https://silo.example/stl-1.stl', facet_count: 1, is_watertight: true };
    default:
      return { token_id: 't', name: 'n', token_type: 'pc', x: 1, y: 1 };
  }
}

describe('forgeToken (TASK-0613)', () => {
  it('posts the token prompt and identity and maps the forged portrait', async () => {
    const { calls, fetchImpl } = stubFetch(() =>
      jsonResponse(200, {
        asset_id: 'tok-0123456789ab',
        image_url: 'https://silo.example/tokens/tok-0123456789ab.png',
        download_url: 'https://silo.example/tokens/tok-0123456789ab.png',
        token_name: 'Thorin Ironbreaker',
        token_type: 'pc',
        crop_style: 'circular',
        size_px: 256,
        has_transparency: true,
        status: 'forged',
      }),
    );

    const token = await forgeToken(
      '',
      { prompt: 'Dwarven paladin', tokenName: 'Thorin Ironbreaker', tokenType: 'pc', campaignId: '' },
      auth,
      fetchImpl,
    );

    assert.equal(calls[0].url, '/api/v1/forge/token');
    assert.deepEqual(calls[0].body, {
      prompt: 'Dwarven paladin',
      token_name: 'Thorin Ironbreaker',
      token_type: 'pc',
    });
    assert.deepEqual(token, {
      asset_id: 'tok-0123456789ab',
      image_url: 'https://silo.example/tokens/tok-0123456789ab.png',
      token_name: 'Thorin Ironbreaker',
      token_type: 'pc',
      size_px: 256,
    });
  });
});

describe('print forge exports (TASK-0613)', () => {
  it('requests the PDF as JSON so the returned download URL can be offered', async () => {
    const { calls, fetchImpl } = stubFetch(() =>
      jsonResponse(200, {
        asset_id: 'pdf-aaaaaaaaaaaa',
        download_url: 'https://silo.example/prints/pdf-aaaaaaaaaaaa.pdf',
        total_pages: 9,
        rows: 3,
        cols: 3,
        page_size: 'letter',
        grid_calibration: '1-inch (72pt)',
        status: 'forged',
      }),
    );

    const result = await exportPrintPdf(
      '',
      { title: 'Crypt', widthCells: 16, heightCells: 16, pageSize: 'letter', campaignId: '' },
      auth,
      fetchImpl,
    );

    assert.equal(calls[0].url, '/api/v1/forge/print-pdf');
    assert.deepEqual(calls[0].body, {
      title: 'Crypt',
      width_cells: 16,
      height_cells: 16,
      page_size: 'letter',
      format: 'json',
    });
    assert.equal(result.asset_id, 'pdf-aaaaaaaaaaaa');
    assert.equal(result.download_url, 'https://silo.example/prints/pdf-aaaaaaaaaaaa.pdf');
  });

  it('posts standees and returns the downloadable sheet', async () => {
    const { calls, fetchImpl } = stubFetch(() =>
      jsonResponse(200, {
        asset_id: 'std-bbbbbbbbbbbb',
        download_url: 'https://silo.example/standees/std-bbbbbbbbbbbb.pdf',
        standee_count: 1,
        pages: 1,
        page_size: 'a4',
        status: 'forged',
      }),
    );

    const result = await exportStandees(
      '',
      {
        sheetTitle: 'Valeros Fighter Standees',
        standees: [{ name: 'Valeros Fighter', type: 'pc', hp: 24, color: '#2a9d8f' }],
        pageSize: 'a4',
        campaignId: '',
      },
      auth,
      fetchImpl,
    );

    assert.equal(calls[0].url, '/api/v1/forge/standees');
    assert.deepEqual(calls[0].body, {
      sheet_title: 'Valeros Fighter Standees',
      standees: [{ name: 'Valeros Fighter', type: 'pc', hp: 24, color: '#2a9d8f' }],
      page_size: 'a4',
      format: 'json',
    });
    assert.equal(result.download_url, 'https://silo.example/standees/std-bbbbbbbbbbbb.pdf');
  });

  it('posts an STL token request and returns the downloadable mesh', async () => {
    const { calls, fetchImpl } = stubFetch(() =>
      jsonResponse(200, {
        asset_id: 'stl-cccccccccccc',
        download_url: 'https://silo.example/stl/stl-cccccccccccc.stl',
        diameter_mm: 28,
        height_mm: 3.5,
        facet_count: 512,
        is_watertight: true,
        condition_label: 'Poisoned',
        status: 'forged',
      }),
    );

    const result = await exportStlToken(
      '',
      { diameterMm: 28, conditionLabel: 'Poisoned', numSlots: 4, campaignId: '' },
      auth,
      fetchImpl,
    );

    assert.equal(calls[0].url, '/api/v1/forge/stl-token');
    assert.deepEqual(calls[0].body, {
      diameter_mm: 28,
      condition_label: 'Poisoned',
      num_slots: 4,
      format: 'json',
    });
    assert.equal(result.download_url, 'https://silo.example/stl/stl-cccccccccccc.stl');
  });

  it('surfaces a 503 from the print route as ForgeApiError', async () => {
    const { fetchImpl } = stubFetch(() =>
      jsonResponse(503, { detail: 'Silo asset storage is unavailable. The asset was not stored.' }),
    );

    await assert.rejects(
      exportStlToken('', { diameterMm: 28, conditionLabel: 'Poisoned', numSlots: 4, campaignId: '' }, auth, fetchImpl),
      (err: unknown) => err instanceof ForgeApiError && err.status === 503,
    );
  });
});

describe('placeBoardToken', () => {
  it('posts the token to the session board route and maps the placed token', async () => {
    const { calls, fetchImpl } = stubFetch(() =>
      jsonResponse(200, {
        token_id: 'tok-1',
        name: 'Thorin Ironbreaker',
        token_type: 'pc',
        x: 4,
        y: 7,
        hp: null,
        is_friendly: true,
        vision_radius: 2,
      }),
    );

    const result = await placeBoardToken(
      '',
      { sessionId: 'session-42', name: 'Thorin Ironbreaker', tokenType: 'pc', x: 4, y: 7 },
      auth,
      fetchImpl,
    );

    assert.equal(calls[0].method, 'POST');
    assert.equal(calls[0].url, '/api/v1/boards/session-42/tokens');
    assert.deepEqual(calls[0].body, {
      name: 'Thorin Ironbreaker',
      token_type: 'pc',
      x: 4,
      y: 7,
    });
    assert.deepEqual(result, { token_id: 'tok-1', name: 'Thorin Ironbreaker', token_type: 'pc', x: 4, y: 7 });
  });

  it('encodes the session id in the route path', async () => {
    const { calls, fetchImpl } = stubFetch(() =>
      jsonResponse(200, { token_id: 't', name: 'n', token_type: 'npc', x: 0, y: 0 }),
    );

    await placeBoardToken('', { sessionId: 'a/b c', name: 'n', tokenType: 'npc', x: 0, y: 0 }, auth, fetchImpl);

    assert.equal(calls[0].url, '/api/v1/boards/a%2Fb%20c/tokens');
  });

  it('throws ForgeApiError with the board detail on 400', async () => {
    const { fetchImpl } = stubFetch(() => jsonResponse(400, { detail: 'Cell is occupied by another token.' }));

    await assert.rejects(
      placeBoardToken('', { sessionId: 's', name: 'n', tokenType: 'pc', x: 1, y: 1 }, auth, fetchImpl),
      (err: unknown) =>
        err instanceof ForgeApiError && err.status === 400 && err.message === 'Cell is occupied by another token.',
    );
  });
});
