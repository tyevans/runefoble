/**
 * AppDataService Owner Wire Suite (TASK-0867, ADR-0015).
 *
 * The mappers read the owner wire shapes. A required field the owner does not send
 * fails the read with { ok: false, status: 502 } and no data. No default is filled in.
 * Fixtures use owner model names (see test/support/owner-wire-fixtures.ts).
 * The gateway is faked at the fetch boundary.
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { AppDataService } from '../src/services/app-data-service.ts';
import { FALLBACK_CHARACTERS } from './support/app-data-service.fixtures.ts';
import {
  OWNER_SESSION_STATE, OWNER_PARTICIPANTS, OWNER_CAMPAIGN_MEMBERS, OWNER_BOARD_STATE, OWNER_BOARD_TOKENS, OWNER_CARAVAN_CONTRACT,
} from './support/owner-wire-fixtures.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

const SESSION_URL = 'GET /api/v1/sessions/session-tomb-14';
const BOARD_URL = 'GET /api/v1/boards/session-tomb-14';
const MEMBERS_URL = 'GET /api/v1/campaigns/4/members';
const CHARACTERS_URL = 'GET /api/v1/characters';

/** Campaign session list item (CampaignSessionResponse, services/game_session/src/game_session/campaign/schemas.py:111). */
const SESSION_LIST_ITEM = {
  id: 'session-tomb-14', campaign_id: '4', title: 'Session #14', status: 'active', round: 3, participants_count: 4, created_at: '2026-11-17T19:00:00Z',
};

function without<T extends object>(body: T, field: string): Record<string, unknown> {
  const copy: Record<string, unknown> = { ...body };
  delete copy[field];
  return copy;
}

function withParticipant(playerId: string, patch: Record<string, unknown>): Record<string, unknown> {
  const entry = { ...(OWNER_PARTICIPANTS as Record<string, Record<string, unknown>>)[playerId], ...patch };
  return { ...OWNER_SESSION_STATE, participants: { ...OWNER_PARTICIPANTS, [playerId]: entry } };
}

function assertFailure(result: { ok: boolean }, pattern: RegExp): void {
  assert.equal(result.ok, false, 'the read must fail');
  assert.equal((result as any).status, 502);
  assert.match((result as any).message, pattern);
  assert.equal('data' in result, false, 'a failed read must not carry data');
}

describe('AppDataService session mapper reads GameSessionState', () => {
  let gateway: FakeGateway;
  let service: AppDataService;

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  it('maps session_id and combat_round from the owner body', async () => {
    gateway = installFakeGateway({ [SESSION_URL]: { body: OWNER_SESSION_STATE } });
    const session = await service.fetchSession('session-tomb-14');
    assert.ok(session.ok);
    assert.equal(session.data.id, 'session-tomb-14');
    assert.equal(session.data.campaignId, '4');
    assert.equal(session.data.title, 'Session #14: Tomb of the Star-Eater');
    assert.equal(session.data.status, 'active');
    assert.equal(session.data.round, 3);
  });

  for (const [field, pattern] of [
    ['session_id', /missing or invalid id\b/],
    ['campaign_id', /campaignId/],
    ['title', /title/],
    ['status', /status/],
    ['combat_round', /round/],
  ] as const) {
    it(`fails when the owner body has no ${field}`, async () => {
      gateway = installFakeGateway({ [SESSION_URL]: { body: without(OWNER_SESSION_STATE, field) } });
      assertFailure(await service.fetchSession('session-tomb-14'), pattern);
    });
  }

  it('fails when the status is an empty string instead of shown as active', async () => {
    gateway = installFakeGateway({ [SESSION_URL]: { body: { ...OWNER_SESSION_STATE, status: '' } } });
    assertFailure(await service.fetchSession('session-tomb-14'), /status/);
  });

  it('fails when combat_round is zero instead of shown as round 1', async () => {
    gateway = installFakeGateway({ [SESSION_URL]: { body: { ...OWNER_SESSION_STATE, combat_round: 0 } } });
    assertFailure(await service.fetchSession('session-tomb-14'), /round/);
  });

  it('does not read round from the list field name, only from combat_round', async () => {
    gateway = installFakeGateway({ [SESSION_URL]: { body: { ...without(OWNER_SESSION_STATE, 'combat_round'), round: 3 } } });
    assertFailure(await service.fetchSession('session-tomb-14'), /round/);
  });

  it('fails when a campaign session list item has no round', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/campaigns/4/sessions': { body: [without(SESSION_LIST_ITEM, 'round')] } });
    assertFailure(await service.fetchCampaignSessions('4'), /round/);
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
      'POST /api/v1/campaigns/4/sessions': { status: 201, body: without(SESSION_LIST_ITEM, 'status') },
    });
    assertFailure(await service.createCampaignSession('4', { title: 'Session #16' }), /status/);
  });
});

describe('AppDataService board mapper reads BoardState', () => {
  let gateway: FakeGateway;
  let service: AppDataService;

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  it('maps cols, rows and the token map to a token list', async () => {
    gateway = installFakeGateway({ [BOARD_URL]: { body: OWNER_BOARD_STATE } });
    const board = await service.fetchBoardState('session-tomb-14');
    assert.ok(board.ok);
    assert.equal(board.data.cols, 12);
    assert.equal(board.data.rows, 10);
    assert.equal(board.data.tokens.length, Object.keys(OWNER_BOARD_TOKENS).length);
    const valeros = board.data.tokens.find((t) => t.id === 'tok-valeros');
    assert.deepEqual(valeros, {
      id: 'tok-valeros', name: 'Valeros', x: 2, y: 3, hp: 38, visionRadius: 4, activeAction: null, characterId: 'char-valeros',
    });
    const ghoul = board.data.tokens.find((t) => t.id === 'tok-ghoul-1');
    assert.equal(ghoul?.hp, undefined, 'a null owner hp maps to no hp');
    assert.equal(ghoul?.activeAction, 'attack');
  });

  it('fails when the board body has no cols instead of a 10 by 10 grid', async () => {
    gateway = installFakeGateway({ [BOARD_URL]: { body: without(OWNER_BOARD_STATE, 'cols') } });
    assertFailure(await service.fetchBoardState('session-tomb-14'), /cols/);
  });

  it('fails when the board body has no rows', async () => {
    gateway = installFakeGateway({ [BOARD_URL]: { body: without(OWNER_BOARD_STATE, 'rows') } });
    assertFailure(await service.fetchBoardState('session-tomb-14'), /rows/);
  });

  it('fails when a token has no token_id', async () => {
    const tokens = { 'tok-valeros': without(OWNER_BOARD_TOKENS['tok-valeros'], 'token_id') };
    gateway = installFakeGateway({ [BOARD_URL]: { body: { ...OWNER_BOARD_STATE, tokens } } });
    assertFailure(await service.fetchBoardState('session-tomb-14'), /token_id/);
  });

  it('fails when the tokens field is a list instead of the owner map', async () => {
    gateway = installFakeGateway({ [BOARD_URL]: { body: { ...OWNER_BOARD_STATE, tokens: [] } } });
    assertFailure(await service.fetchBoardState('session-tomb-14'), /tokens/);
  });

  it('treats an absent token map as an empty board, because tokens is optional', async () => {
    gateway = installFakeGateway({ [BOARD_URL]: { body: { cols: 8, rows: 8 } } });
    const board = await service.fetchBoardState('session-tomb-14');
    assert.ok(board.ok);
    assert.deepEqual(board.data.tokens, []);
  });
});

describe('AppDataService lobby reads participants from the owner map', () => {
  let gateway: FakeGateway;
  let service: AppDataService;

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  const routes = (state: unknown, members: unknown = OWNER_CAMPAIGN_MEMBERS) => ({
    [SESSION_URL]: { body: state },
    [MEMBERS_URL]: { body: members },
    [CHARACTERS_URL]: { body: FALLBACK_CHARACTERS },
  });

  it('maps the participant map to a roster with readiness and absence', async () => {
    gateway = installFakeGateway(routes(OWNER_SESSION_STATE));
    const lobby = await service.fetchLobbyState('4', 'session-tomb-14');
    assert.ok(lobby.ok);
    assert.deepEqual(lobby.data.participants, [
      {
        userId: 'user-fixture', username: 'Valeros', role: 'owner', isReady: true, isAbsent: false,
        characterId: 'char-valeros', characterName: 'Valeros of Korvosa', characterClass: 'Fighter',
      },
      {
        userId: 'user-kyra', username: 'Kyra', role: 'player', isReady: false, isAbsent: true,
        characterId: 'char-kyra', characterName: 'Kyra the Sun Maiden', characterClass: 'Cleric',
      },
    ]);
    assert.equal(lobby.data.availableCharacters[0].id, 'char-valeros');
  });

  it('fails when the owner sends participants as a list', async () => {
    gateway = installFakeGateway(routes({ ...OWNER_SESSION_STATE, participants: [] }));
    assertFailure(await service.fetchLobbyState('4', 'session-tomb-14'), /participants/);
  });

  it('fails when a participant has no character_id', async () => {
    gateway = installFakeGateway(routes(withParticipant('user-kyra', { character_id: undefined })));
    assertFailure(await service.fetchLobbyState('4', 'session-tomb-14'), /character_id/);
  });

  it('fails when a participant has no campaign member to name them', async () => {
    gateway = installFakeGateway(routes(OWNER_SESSION_STATE, [OWNER_CAMPAIGN_MEMBERS[0]]));
    assertFailure(await service.fetchLobbyState('4', 'session-tomb-14'), /no campaign member for participant user-kyra/);
  });

  it('fails when the matching campaign member has no username', async () => {
    const members = [OWNER_CAMPAIGN_MEMBERS[0], { ...OWNER_CAMPAIGN_MEMBERS[1], username: null }];
    gateway = installFakeGateway(routes(OWNER_SESSION_STATE, members));
    assertFailure(await service.fetchLobbyState('4', 'session-tomb-14'), /username/);
  });
});

describe('AppDataService caravan board reads the owner contract list', () => {
  let gateway: FakeGateway;
  let service: AppDataService;

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  it('returns the contract list the owner sends, unchanged', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/shared-worlds/world-1/caravans/contracts': { body: { shared_world_id: 'world-1', contracts: [OWNER_CARAVAN_CONTRACT] } },
    });
    const contracts = await service.fetchCaravanContracts('world-1');
    assert.ok(contracts.ok);
    assert.deepEqual(contracts.data, [OWNER_CARAVAN_CONTRACT]);
  });

  it('fails when the body has no contracts list', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/shared-worlds/world-1/caravans/contracts': { body: {} } });
    const contracts = await service.fetchCaravanContracts('world-1');
    assert.equal(contracts.ok, false);
    assert.equal((contracts as any).status, 502);
  });
});

describe('AppDataService session state reads every participant seat (TASK-0974)', () => {
  let gateway: FakeGateway;
  let service: AppDataService;

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  it('maps the status and each seat with its stand-in state', async () => {
    gateway = installFakeGateway({ [SESSION_URL]: { body: OWNER_SESSION_STATE } });
    const state = await service.fetchSessionState('session-tomb-14');
    assert.ok(state.ok);
    assert.equal(state.data.status, 'active');
    assert.deepEqual(state.data.participants[1], {
      userId: 'user-kyra', characterId: 'char-kyra', characterName: 'Kyra the Sun Maiden', isStandInActive: false,
    });
  });

  it('fails when a participant has no is_stand_in_active', async () => {
    gateway = installFakeGateway({ [SESSION_URL]: { body: withParticipant('user-kyra', { is_stand_in_active: undefined }) } });
    assertFailure(await service.fetchSessionState('session-tomb-14'), /is_stand_in_active/);
  });

  it('fails when the owner sends participants as a list', async () => {
    gateway = installFakeGateway({ [SESSION_URL]: { body: { ...OWNER_SESSION_STATE, participants: [] } } });
    assertFailure(await service.fetchSessionState('session-tomb-14'), /participants/);
  });
});
