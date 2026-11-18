/**
 * Frontend Blackbox Test Suite: Campaign Sessions Scoping, Scheduling & Result Contract.
 * TASK-0354: Dynamic Campaign Sessions Scoping, Scheduling & Offline Cache.
 * TASK-0640: The client no longer invents sessions. Reads return the gateway list or a typed error.
 * Governing ADRs: ADR-0004, ADR-0007, ADR-0013, ADR-0014.
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';

import { AppDataService } from '../src/services/app-data-service.ts';
import { FALLBACK_CAMPAIGN_SESSIONS_MAP } from './support/app-data-service.fixtures.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

/** A gateway whose session rosters are stored per campaign. Creates append to the roster. */
function installSessionGateway(initial: Record<string, any[]>): { gateway: FakeGateway; rosters: Record<string, any[]> } {
  const rosters: Record<string, any[]> = JSON.parse(JSON.stringify(initial));
  const gateway = installFakeGateway({
    '*': (req) => {
      const match = /^\/api\/v1\/campaigns\/([^/]+)\/sessions$/.exec(req.path);
      if (match && req.method === 'GET') return { body: rosters[match[1]] ?? [] };
      if (match && req.method === 'POST') {
        const campaignId = match[1];
        const body = req.body as any;
        const created = { id: `lobby-${campaignId}-${(rosters[campaignId]?.length ?? 0) + 1}`, campaign_id: campaignId, title: body.title, status: body.status ?? 'lobby', round: 1, participants_count: 0, description: body.description };
        rosters[campaignId] = [...(rosters[campaignId] ?? []), created];
        return { status: 201, body: created };
      }
      const single = /^\/api\/v1\/sessions\/([^/]+)$/.exec(req.path);
      if (single && req.method === 'GET') {
        const found = Object.values(rosters).flat().find((s: any) => s.id === single[1]);
        return found ? { body: found } : { status: 404, body: { detail: 'Session not found' } };
      }
      return { status: 500, body: { detail: `No fake route for ${req.method} ${req.path}` } };
    },
  });
  return { gateway, rosters };
}

describe('TASK-0354: Campaign Sessions Scoping', () => {
  let gateway: FakeGateway | undefined;

  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('returns an empty roster for a new campaign and does not invent a lobby session', async () => {
    ({ gateway } = installSessionGateway({}));
    const result = await new AppDataService().fetchCampaignSessions('test-camp-new');
    assert.deepEqual(result, { ok: true, data: [] });
  });

  it('returns only the sessions that belong to the requested campaign', async () => {
    ({ gateway } = installSessionGateway({
      '4': FALLBACK_CAMPAIGN_SESSIONS_MAP['4'].map((s) => ({ ...s, campaign_id: '4' })),
      '5': FALLBACK_CAMPAIGN_SESSIONS_MAP['5'].map((s) => ({ ...s, campaign_id: '5' })),
    }));
    const service = new AppDataService();
    const camp4 = await service.fetchCampaignSessions('4');
    const camp5 = await service.fetchCampaignSessions('5');
    assert.ok(camp4.ok && camp5.ok);
    assert.equal(camp4.data.length, 2);
    assert.equal(camp5.data.length, 1);
    assert.ok(camp4.data.every((s) => s.campaignId === '4'));
    assert.ok(camp5.data.every((s) => s.campaignId === '5'));
    assert.equal(camp5.data[0].status, 'upcoming');
  });

  it('persists newly scheduled sessions across fetchCampaignSessions reloads', async () => {
    ({ gateway } = installSessionGateway({ 'camp-persist': [] }));
    const service = new AppDataService();
    const initial = await service.fetchCampaignSessions('camp-persist');
    assert.ok(initial.ok);
    assert.equal(initial.data.length, 0);

    const created = await service.createCampaignSession('camp-persist', {
      title: 'Chapter 2: The Crypt of the Undying',
      status: 'upcoming',
      scheduled_at: '2026-11-01T18:00:00Z',
      description: 'Dungeon infiltration past the skeletal sentinels.',
    });
    assert.ok(created.ok);
    assert.equal(created.data.campaignId, 'camp-persist');
    assert.equal(created.data.title, 'Chapter 2: The Crypt of the Undying');
    assert.equal(created.data.status, 'upcoming');

    const reloaded = await service.fetchCampaignSessions('camp-persist');
    assert.ok(reloaded.ok);
    assert.equal(reloaded.data.length, 1);
    assert.equal(reloaded.data[0].title, 'Chapter 2: The Crypt of the Undying');

    const fetched = await service.fetchSession(created.data.id);
    assert.ok(fetched.ok);
    assert.equal(fetched.data.id, created.data.id);
    assert.equal(fetched.data.title, 'Chapter 2: The Crypt of the Undying');
  });

  it('reports a failed session read as a typed error and never as an empty roster', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/campaigns/4/sessions': { status: 503, body: { detail: 'Session service unavailable' } } });
    const result = await new AppDataService().fetchCampaignSessions('4');
    assert.equal(result.ok, false);
    assert.equal(result.ok === false && result.status, 503);
    assert.equal(result.ok === false && result.message, 'Session service unavailable');
  });

  it('reports a failed session create and leaves the roster unchanged', async () => {
    gateway = installFakeGateway({ 'POST /api/v1/campaigns/camp-x/sessions': { status: 400, body: { detail: 'title is required' } } });
    const result = await new AppDataService().createCampaignSession('camp-x', { title: '' });
    assert.equal(result.ok, false);
    assert.equal(result.ok === false && result.message, 'title is required');
  });
});
