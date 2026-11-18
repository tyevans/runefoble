/**
 * Codex Entry Create Tests (TASK-0695).
 *
 * The codex form builds the entry. The App Shell publishes it through the gateway, which is
 * faked at the fetch boundary. A refused write must report the error and never invent an entry.
 * Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { AppDataService } from '../src/services/app-data-service.ts';
import { createCodexEntry, fetchCampaignLoreEntries } from '../src/services/campaign-hub-client.ts';
import { buildEntryDetail } from '../../services/campaign_lore/ui/src/codex/entry-form.template.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

const CAMPAIGN_ID = 'c-77';
const ROUTE = `/api/v1/campaigns/${CAMPAIGN_ID}/codex/entries`;
const PAYLOAD = { title: 'Star-Eater Gate', content: 'A gate of black glass.', privacy: 'party_shared' };
const OWNER_ENTRY = { entry_id: 'e-1', ...PAYLOAD, linked_entities: [] };

describe('The codex form builds the entry to publish', () => {
  it('trims the title and the text', () => {
    const entry = buildEntryDetail({ title: '  Gate ', content: ' Black glass. ', privacy: 'private' });
    assert.deepEqual(entry, { title: 'Gate', content: 'Black glass.', privacy: 'private' });
  });

  it('refuses a blank title or a blank text', () => {
    assert.equal(buildEntryDetail({ title: ' ', content: 'x', privacy: 'public' }), null);
    assert.equal(buildEntryDetail({ title: 'x', content: '  ', privacy: 'public' }), null);
  });
});

describe('Codex entries are published through the gateway', () => {
  let gateway: FakeGateway;
  let service: AppDataService;
  const write = () => service.request.bind(service);

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  it('posts the entry to the gateway codex entries route and returns the owner entry', async () => {
    gateway = installFakeGateway({ [`POST ${ROUTE}`]: { status: 201, body: OWNER_ENTRY } });
    const res = await createCodexEntry(write(), CAMPAIGN_ID, PAYLOAD);

    assert.ok(res.ok);
    assert.equal(res.data.entry_id, 'e-1');
    assert.deepEqual(gateway.calls[0].body, PAYLOAD);
  });

  it('returns the gateway refusal and never a local entry', async () => {
    gateway = installFakeGateway({ [`POST ${ROUTE}`]: { status: 503, body: { detail: 'Campaign lore is unavailable.' } } });
    const res = await createCodexEntry(write(), CAMPAIGN_ID, PAYLOAD);

    assert.deepEqual(res, { ok: false, status: 503, message: 'Campaign lore is unavailable.' });
  });

  it('fails when the owner answers without an entry id', async () => {
    gateway = installFakeGateway({ [`POST ${ROUTE}`]: { status: 201, body: { ok: true } } });
    const res = await createCodexEntry(write(), CAMPAIGN_ID, PAYLOAD);

    assert.equal(res.ok, false);
  });

  it('lists the published entry when the codex is read again', async () => {
    gateway = installFakeGateway({ [`GET /api/v1/campaigns/${CAMPAIGN_ID}/codex`]: { body: [OWNER_ENTRY] } });
    const res = await fetchCampaignLoreEntries(write(), CAMPAIGN_ID);

    assert.ok(res.ok);
    assert.deepEqual(res.data.map((e) => e.title), ['Star-Eater Gate']);
  });
});
