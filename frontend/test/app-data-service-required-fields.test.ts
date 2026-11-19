/**
 * AppDataService Required Fields Suite (TASK-0867, ADR-0015).
 *
 * A mapper never fills a missing required field with a default. A gateway body that
 * lacks a required field returns { ok: false, status: 502 } and no data.
 * The gateway is faked at the fetch boundary.
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { AppDataService } from '../src/services/app-data-service.ts';
import { FALLBACK_CHARACTERS } from './support/app-data-service.fixtures.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

const SESSION_BODY = {
  id: 'session-tomb-14', campaign_id: '4', title: 'Session #14: Tomb of the Star-Eater',
  status: 'active', round: 3, participants: [],
};

const SESSION_LIST_ITEM = {
  id: 'session-tomb-14', campaign_id: '4', title: 'Session #14', status: 'active', round: 3, participants_count: 4,
};

function withoutField(body: Record<string, unknown>, field: string): Record<string, unknown> {
  const copy = { ...body };
  delete copy[field];
  return copy;
}

function assertRequiredFieldFailure(result: { ok: boolean }, field: string): void {
  assert.equal(result.ok, false, `a body without ${field} must fail`);
  assert.equal((result as any).status, 502);
  assert.match((result as any).message, new RegExp(`missing or invalid.*${field}`));
  assert.equal('data' in result, false, 'a failed mapper must not carry data');
}

describe('AppDataService session mapper requires its fields', () => {
  let gateway: FakeGateway;
  let service: AppDataService;

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  it('maps a complete session body to the same values as before', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/sessions/session-tomb-14': { body: SESSION_BODY } });
    const session = await service.fetchSession('session-tomb-14');
    assert.ok(session.ok);
    assert.equal(session.data.id, 'session-tomb-14');
    assert.equal(session.data.campaignId, '4');
    assert.equal(session.data.title, 'Session #14: Tomb of the Star-Eater');
    assert.equal(session.data.status, 'active');
    assert.equal(session.data.round, 3);
  });

  for (const field of ['campaign_id', 'title', 'status', 'round']) {
    it(`fails when the session body has no ${field}`, async () => {
      gateway = installFakeGateway({
        'GET /api/v1/sessions/session-tomb-14': { body: withoutField(SESSION_BODY, field) },
      });
      const session = await service.fetchSession('session-tomb-14');
      const expected = field === 'campaign_id' ? 'campaignId' : field;
      assertRequiredFieldFailure(session, expected);
    });
  }

  it('fails when the session status is an empty string instead of shown as active', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/sessions/session-tomb-14': { body: { ...SESSION_BODY, status: '' } },
    });
    assertRequiredFieldFailure(await service.fetchSession('session-tomb-14'), 'status');
  });

  it('fails when the round is zero instead of shown as round 1', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/sessions/session-tomb-14': { body: { ...SESSION_BODY, round: 0 } },
    });
    assertRequiredFieldFailure(await service.fetchSession('session-tomb-14'), 'round');
  });

  it('fails when a campaign session list item has no round', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/campaigns/4/sessions': { body: [withoutField(SESSION_LIST_ITEM, 'round')] },
    });
    assertRequiredFieldFailure(await service.fetchCampaignSessions('4'), 'round');
  });

  it('maps a complete campaign session list', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/campaigns/4/sessions': { body: [SESSION_LIST_ITEM] } });
    const sessions = await service.fetchCampaignSessions('4');
    assert.ok(sessions.ok);
    assert.equal(sessions.data.length, 1);
    assert.equal(sessions.data[0].campaignId, '4');
    assert.equal(sessions.data[0].round, 3);
  });

  it('fails when the campaign session response is not a list', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/campaigns/4/sessions': { body: { sessions: [] } } });
    const sessions = await service.fetchCampaignSessions('4');
    assert.equal(sessions.ok, false);
    assert.equal((sessions as any).status, 502);
  });

  it('fails the create call when the created session has no status', async () => {
    gateway = installFakeGateway({
      'POST /api/v1/campaigns/4/sessions': { status: 201, body: withoutField(SESSION_LIST_ITEM, 'status') },
    });
    assertRequiredFieldFailure(await service.createCampaignSession('4', { title: 'Session #16' }), 'status');
  });
});

describe('AppDataService board mapper requires its size', () => {
  let gateway: FakeGateway;
  let service: AppDataService;

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  it('maps a complete board body to the same values as before', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/boards/session-tomb-14': { body: { cols: 12, rows: 9, tokens: [] } },
    });
    const board = await service.fetchBoardState('session-tomb-14');
    assert.ok(board.ok);
    assert.equal(board.data.cols, 12);
    assert.equal(board.data.rows, 9);
    assert.deepEqual(board.data.tokens, []);
  });

  it('fails when the board body has no cols instead of a 10 by 10 grid', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/boards/session-tomb-14': { body: { rows: 10, tokens: [] } },
    });
    assertRequiredFieldFailure(await service.fetchBoardState('session-tomb-14'), 'cols');
  });

  it('fails when the board body has no rows', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/boards/session-tomb-14': { body: { cols: 10, tokens: [] } },
    });
    assertRequiredFieldFailure(await service.fetchBoardState('session-tomb-14'), 'rows');
  });

  it('fails the token read with the same board failure', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/boards/session-tomb-14': { body: { tokens: [] } },
    });
    const tokens = await service.fetchBoardTokens('session-tomb-14');
    assert.equal(tokens.ok, false);
  });

  it('treats an absent token list as an empty board, because tokens is optional', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/boards/session-tomb-14': { body: { cols: 8, rows: 8 } } });
    const board = await service.fetchBoardState('session-tomb-14');
    assert.ok(board.ok);
    assert.deepEqual(board.data.tokens, []);
  });
});

describe('AppDataService lobby and caravan mappers require their lists', () => {
  let gateway: FakeGateway;
  let service: AppDataService;

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  it('fails the lobby read when the session has no participant list', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/sessions/session-tomb-14': { body: withoutField(SESSION_BODY, 'participants') },
      'GET /api/v1/characters': { body: FALLBACK_CHARACTERS },
    });
    const lobby = await service.fetchLobbyState('4', 'session-tomb-14');
    assert.equal(lobby.ok, false);
    assert.equal((lobby as any).status, 502);
  });

  it('fails the caravan board read when the body has no contracts list', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/shared-worlds/world-1/caravans/contracts': { body: {} },
    });
    const contracts = await service.fetchCaravanContracts('world-1');
    assert.equal(contracts.ok, false);
    assert.equal((contracts as any).status, 502);
  });

  it('returns the contracts list when the body carries it', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/shared-worlds/world-1/caravans/contracts': { body: { contracts: [] } },
    });
    assert.deepEqual(await service.fetchCaravanContracts('world-1'), { ok: true, data: [] });
  });
});
