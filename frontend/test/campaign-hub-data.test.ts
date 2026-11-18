/**
 * Campaign Hub Live Data Tests (TASK-0646).
 *
 * The Codex & Lore and Chronicle & Stats tabs read through the gateway. The gateway is
 * faked at the fetch boundary. A failed or misshapen response must surface as a failure,
 * never as an empty or canned dataset. Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { AppDataService } from '../src/services/app-data-service.ts';
import { fetchCampaignAnalyticsView, fetchCampaignAtlasView, fetchCampaignLoreEntries, toLoreEntry } from '../src/services/campaign-hub-client.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

const CAMPAIGN_ID = 'c-42';
const LIVE_PIN = { pin_id: 'pin-1', title: 'Star-Eater Gate', layer: 'continental', coordinates: { x: 120, y: 240 } };
const LIVE_ENTRY = {
  entry_id: 'entry-9', title: 'The Star-Eater Relic', content: 'An obsidian sphere.', privacy: 'party_shared',
  linked_entities: [{ id: 'npc-1', name: 'Brother Ohm', entity_type: 'npc' }],
};
const HEATMAP = { campaign_id: CAMPAIGN_ID, cells: [], grid_cols: 8, grid_rows: 8 };
const MVP = { campaign_id: CAMPAIGN_ID, combatants: [], awards: [] };
const TIMELINE = { campaign_id: CAMPAIGN_ID, total_milestones: 1, milestones: [{ title: 'Breach of the Astral Crypt' }] };

describe('Campaign hub views read live gateway data', () => {
  let gateway: FakeGateway;
  let service: AppDataService;
  const request = () => service.request.bind(service);

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  it('reads atlas pins and territories from the gateway atlas route', async () => {
    gateway = installFakeGateway({
      [`GET /api/v1/campaigns/${CAMPAIGN_ID}/atlas`]: { body: { campaign_id: CAMPAIGN_ID, pins: [LIVE_PIN], territories: [] } },
    });
    const res = await fetchCampaignAtlasView(request(), CAMPAIGN_ID);
    assert.ok(res.ok);
    assert.deepEqual(res.data.pins.map((p) => p.title), ['Star-Eater Gate']);
    assert.deepEqual(res.data.territories, []);
  });

  it('maps codex entries from the gateway codex route to the codex element shape', async () => {
    gateway = installFakeGateway({ [`GET /api/v1/campaigns/${CAMPAIGN_ID}/codex`]: { body: [LIVE_ENTRY] } });
    const res = await fetchCampaignLoreEntries(request(), CAMPAIGN_ID);
    assert.ok(res.ok);
    assert.deepEqual(res.data, [{ id: 'entry-9', title: 'The Star-Eater Relic', text: 'An obsidian sphere.', entities: ['Brother Ohm'], isSecret: false }]);
  });

  it('reads heatmap, MVP, and timeline from the gateway analytics routes', async () => {
    gateway = installFakeGateway({
      [`GET /api/v1/analytics/campaigns/${CAMPAIGN_ID}/heatmap`]: { body: HEATMAP },
      [`GET /api/v1/analytics/campaigns/${CAMPAIGN_ID}/mvp`]: { body: MVP },
      [`GET /api/v1/analytics/campaigns/${CAMPAIGN_ID}/timeline`]: { body: TIMELINE },
    });
    const res = await fetchCampaignAnalyticsView(request(), CAMPAIGN_ID);
    assert.ok(res.ok);
    assert.equal(res.data.timeline.milestones[0].title, 'Breach of the Astral Crypt');
  });

  it('returns the gateway failure for atlas and never substitutes data', async () => {
    gateway = installFakeGateway({
      [`GET /api/v1/campaigns/${CAMPAIGN_ID}/atlas`]: { status: 503, body: { detail: 'Campaign lore is unavailable.' } },
    });
    const res = await fetchCampaignAtlasView(request(), CAMPAIGN_ID);
    assert.deepEqual(res, { ok: false, status: 503, message: 'Campaign lore is unavailable.' });
  });

  it('rejects a codex response that is not a list instead of rendering it as entries', async () => {
    gateway = installFakeGateway({ [`GET /api/v1/campaigns/${CAMPAIGN_ID}/codex`]: { body: { entries: [LIVE_ENTRY] } } });
    const res = await fetchCampaignLoreEntries(request(), CAMPAIGN_ID);
    assert.equal(res.ok, false);
  });

  it('fails the analytics read when any one route fails', async () => {
    gateway = installFakeGateway({
      [`GET /api/v1/analytics/campaigns/${CAMPAIGN_ID}/heatmap`]: { body: HEATMAP },
      [`GET /api/v1/analytics/campaigns/${CAMPAIGN_ID}/mvp`]: { status: 403, body: { detail: 'Forbidden' } },
      [`GET /api/v1/analytics/campaigns/${CAMPAIGN_ID}/timeline`]: { body: TIMELINE },
    });
    const res = await fetchCampaignAnalyticsView(request(), CAMPAIGN_ID);
    assert.equal(res.ok, false);
    assert.equal(res.ok === false && res.status, 403);
  });

  it('maps a private entry to isSecret and tolerates unnamed links', () => {
    const entry = toLoreEntry({ entry_id: 'e', title: 't', content: 'c', privacy: 'private', linked_entities: [{ id: 'x' }, 'Plain'] });
    assert.equal(entry.isSecret, true);
    assert.deepEqual(entry.entities, ['Plain']);
  });
});

describe('App Shell hub templates wire live data (TASK-0646)', () => {
  const viewTemplates = readFileSync(fileURLToPath(new URL('../src/views/campaign-hub-view.ts', import.meta.url)), 'utf8');
  const analyticsElement = readFileSync(fileURLToPath(new URL('../../services/campaign_analytics/ui/src/runefoble-campaign-analytics.ts', import.meta.url)), 'utf8');

  it('never passes an empty apiBaseUrl to the analytics element', () => {
    assert.equal(viewTemplates.includes('apiBaseUrl=""'), false);
    assert.equal(analyticsElement.includes('apiBaseUrl'), false);
  });

  it('mounts both the atlas and the lore codex behind codex sub-tabs', () => {
    assert.ok(viewTemplates.includes('<runefoble-campaign-atlas'));
    assert.ok(viewTemplates.includes('<runefoble-campaign-codex'));
    assert.ok(viewTemplates.includes('campaignCodexView'));
  });

  it('the analytics element performs no network calls of its own', () => {
    assert.equal(analyticsElement.includes('fetch('), false);
  });
});
