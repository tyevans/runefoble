/**
 * Atlas Pin Create Tests (TASK-0695).
 *
 * The App Shell places a pin through the gateway, then reloads the atlas. The gateway is faked
 * at the fetch boundary. A refused write must leave the pin list unchanged and report the error.
 * Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { AppDataService } from '../src/services/app-data-service.ts';
import { createAtlasPin, fetchCampaignAtlasView } from '../src/services/campaign-hub-client.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

const CAMPAIGN_ID = 'c-77';
const PAYLOAD = { title: 'Star-Eater Gate', coordinates: { x: 320, y: 180 }, layer: 'continental' };
const OWNER_PIN = { pin_id: 'pin-9', ...PAYLOAD };

describe('Atlas pins are placed through the gateway', () => {
  let gateway: FakeGateway;
  let service: AppDataService;
  const write = () => service.request.bind(service);

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  it('posts the pin to the gateway atlas pin route and returns the owner pin', async () => {
    gateway = installFakeGateway({ [`POST /api/v1/campaigns/${CAMPAIGN_ID}/atlas/pins`]: { status: 201, body: OWNER_PIN } });
    const res = await createAtlasPin(write(), CAMPAIGN_ID, PAYLOAD);

    assert.ok(res.ok);
    assert.equal(res.data.pin_id, 'pin-9');
    assert.deepEqual(gateway.calls[0].body, PAYLOAD);
  });

  it('returns the gateway refusal and never a local pin', async () => {
    gateway = installFakeGateway({
      [`POST /api/v1/campaigns/${CAMPAIGN_ID}/atlas/pins`]: { status: 503, body: { detail: 'Campaign lore is unavailable.' } },
    });
    const res = await createAtlasPin(write(), CAMPAIGN_ID, PAYLOAD);

    assert.deepEqual(res, { ok: false, status: 503, message: 'Campaign lore is unavailable.' });
  });

  it('fails when the owner answers without a pin id', async () => {
    gateway = installFakeGateway({ [`POST /api/v1/campaigns/${CAMPAIGN_ID}/atlas/pins`]: { status: 201, body: { ok: true } } });
    const res = await createAtlasPin(write(), CAMPAIGN_ID, PAYLOAD);

    assert.equal(res.ok, false);
  });

  it('reloads the atlas view after a placed pin is listed', async () => {
    gateway = installFakeGateway({
      [`GET /api/v1/campaigns/${CAMPAIGN_ID}/atlas`]: { body: { campaign_id: CAMPAIGN_ID, pins: [OWNER_PIN], territories: [] } },
    });
    const res = await fetchCampaignAtlasView(write(), CAMPAIGN_ID);

    assert.ok(res.ok);
    assert.deepEqual(res.data.pins.map((p) => p.title), ['Star-Eater Gate']);
  });
});
