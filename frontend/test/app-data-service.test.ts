/**
 * AppDataService Result Contract Test Suite (TASK-0640).
 *
 * Every public read and write returns a DataResult. A failed gateway call returns
 * { ok: false } and never canned data. The gateway is faked at the fetch boundary.
 * Governing ADRs: ADR-0004, ADR-0007, ADR-0014
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { AppDataService } from '../src/services/app-data-service.ts';
import {
  FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS, FALLBACK_MEMBERS,
  FALLBACK_CAMPAIGN_SESSIONS_MAP,
} from './support/app-data-service.fixtures.ts';
import {
  OWNER_SESSION_STATE, OWNER_CAMPAIGN_MEMBERS, OWNER_BOARD_STATE, OWNER_BOARD_TOKENS,
} from './support/owner-wire-fixtures.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';


describe('AppDataService success path through the gateway', () => {
  let gateway: FakeGateway;
  let service: AppDataService;

  beforeEach(() => { service = new AppDataService(); });
  afterEach(() => gateway?.restore());

  it('reads campaigns, campaign, members, and sessions from gateway responses', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/campaigns': { body: FALLBACK_CAMPAIGNS },
      'GET /api/v1/campaigns/4': { body: FALLBACK_CAMPAIGNS[0] },
      'GET /api/v1/campaigns/4/members': { body: FALLBACK_MEMBERS },
      'GET /api/v1/campaigns/4/sessions': { body: FALLBACK_CAMPAIGN_SESSIONS_MAP['4'] },
      'GET /api/v1/sessions/session-tomb-14': { body: OWNER_SESSION_STATE },
    });

    const campaigns = await service.fetchCampaigns();
    assert.equal(campaigns.ok, true);
    assert.equal(campaigns.ok && campaigns.data.length, FALLBACK_CAMPAIGNS.length);

    const campaign = await service.fetchCampaign('4');
    assert.ok(campaign.ok);
    assert.equal(campaign.data.title, 'Tomb of the Star-Eater');

    const members = await service.fetchCampaignMembers('4');
    assert.ok(members.ok);
    assert.equal(members.data.length, 3);

    const sessions = await service.fetchCampaignSessions('4');
    assert.ok(sessions.ok);
    assert.equal(sessions.data[0].campaignId, '4');

    const session = await service.fetchSession('session-tomb-14');
    assert.ok(session.ok);
  });

  it('reads characters, board state, and lobby state from gateway responses', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters': { body: FALLBACK_CHARACTERS },
      'GET /api/v1/characters/char-valeros': { body: FALLBACK_CHARACTERS[0] },
      'GET /api/v1/sessions/session-tomb-14': { body: OWNER_SESSION_STATE },
      'GET /api/v1/boards/session-tomb-14': { body: OWNER_BOARD_STATE },
      'GET /api/v1/campaigns/4/members': { body: OWNER_CAMPAIGN_MEMBERS },
    });

    const character = await service.fetchCharacter('char-valeros');
    assert.ok(character.ok);
    assert.equal(character.data.name, 'Valeros of Korvosa');

    const board = await service.fetchBoardState('session-tomb-14');
    assert.ok(board.ok);
    assert.equal(board.data.cols, 12);
    assert.equal(board.data.tokens.length, Object.keys(OWNER_BOARD_TOKENS).length);

    const tokens = await service.fetchBoardTokens('session-tomb-14');
    assert.ok(tokens.ok);
    assert.equal(tokens.data[0].name, 'Valeros');

    const lobby = await service.fetchLobbyState('4', 'session-tomb-14');
    assert.ok(lobby.ok);
    assert.equal(lobby.data.participants[0].characterName, 'Valeros of Korvosa');
    assert.equal(lobby.data.availableCharacters[0].id, 'char-valeros');
  });

  it('reads the session chronicle from the gateway and maps each line to a feed row', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/sessions/session-tomb-14/events': { body: [
        { event_id: 'evt-1', kind: 'session_started', occurred_at: '2026-11-17T19:45:00Z', speaker: 'system', text: 'Session started.', penalties: [] },
        { event_id: 'evt-2', kind: 'stand_in_action', occurred_at: '2026-11-17T19:45:20Z', speaker: 'Kyra', text: 'Hah!', action_type: 'attack', penalties: ['drunk'] },
        { event_id: 'evt-3', kind: 'dice_roll', occurred_at: '2026-11-17T19:45:30Z', speaker: 'Valeros', text: '1d20 = 14', action_type: 'dice_roll', penalties: [] },
      ] },
    });
    const events = await service.fetchSessionEvents('session-tomb-14');
    assert.equal(gateway.calls.length, 1);
    assert.ok(events.ok);
    assert.deepEqual(events.data.map((e) => [e.id, e.source, e.speaker, e.text, e.actionType]), [
      ['evt-1', 'system', 'system', 'Session started.', undefined],
      ['evt-2', 'stand_in', 'Kyra', 'Hah!', 'speech'],
      ['evt-3', 'player', 'Valeros', '1d20 = 14', 'dice_roll'],
    ]);
  });

  it('returns an empty session feed when the session has no chronicle lines', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/sessions/session-new/events': { body: [] } });
    assert.deepEqual(await service.fetchSessionEvents('session-new'), { ok: true, data: [] });
  });

  it('returns a failure, not fixture rows, when the chronicle read fails', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/sessions/session-tomb-14/events': { status: 503, body: { detail: 'down' } } });
    const events = await service.fetchSessionEvents('session-tomb-14');
    assert.equal(events.ok, false);
  });

  it('creates, assigns, and deletes a character against the gateway', async () => {
    const roster = [...FALLBACK_CHARACTERS];
    const created = { id: 'char-new', name: 'Harsk the Ranger', characterClass: 'Ranger', level: 3, maxHp: 28, currentHp: 28, armorClass: 15, speed: 30, campaignId: null, campaignTitle: null };
    gateway = installFakeGateway({
      'POST /api/v1/characters': { status: 201, body: created },
      'GET /api/v1/characters': () => ({ body: roster }),
      'PATCH /api/v1/characters/char-new/campaign': () => { roster.push({ ...created, campaignId: '4' }); return { status: 204 }; },
      'DELETE /api/v1/characters/char-new': { status: 204 },
    });

    const result = await service.createCharacter({ name: 'Harsk the Ranger', characterClass: 'Ranger', subclass: 'Hunter', level: 3, maxHp: 28, armorClass: 15, speed: 30 } as any);
    assert.ok(result.ok);
    assert.equal(result.data.name, 'Harsk the Ranger');

    const assigned = await service.assignCharacterCampaign('char-new', '4');
    assert.equal(assigned.ok, true);
    const afterAssign = await service.fetchCharacters();
    assert.ok(afterAssign.ok);
    assert.equal(afterAssign.data.find((c) => c.id === 'char-new')?.campaignId, '4');

    const deleted = await service.deleteCharacter('char-new');
    assert.equal(deleted.ok, true);
    assert.equal(gateway.calls.at(-1)?.method, 'DELETE');
  });

  it('creates a campaign and a campaign session from the gateway response', async () => {
    gateway = installFakeGateway({
      'POST /api/v1/campaigns': { status: 201, body: { id: 'camp-9', title: 'Ashen Keep', role: 'owner', player_count: 1 } },
      'POST /api/v1/campaigns/4/sessions': { status: 201, body: { id: 'lobby-9', campaign_id: '4', title: 'Session #16', status: 'lobby', round: 1, participants_count: 0 } },
    });

    const campaign = await service.createCampaign({ title: 'Ashen Keep' } as any);
    assert.ok(campaign.ok);
    assert.equal(campaign.data.id, 'camp-9');

    const session = await service.createCampaignSession('4', { title: 'Session #16' });
    assert.ok(session.ok);
    assert.equal(session.data.campaignId, '4');
    assert.equal(session.data.participantsCount, 0);
  });
});

describe('AppDataService failure path returns typed errors, never fixture data', () => {
  let gateway: FakeGateway;
  let service: AppDataService;

  beforeEach(() => {
    service = new AppDataService();
    gateway = installFakeGateway({ '*': { status: 500, body: { detail: 'boom' } } });
  });
  afterEach(() => gateway.restore());

  const calls: Array<[string, () => Promise<{ ok: boolean }>]> = [
    ['fetchCampaigns', () => service.fetchCampaigns()],
    ['fetchProfile', () => service.fetchProfile()],
    ['fetchCampaign', () => service.fetchCampaign('4')],
    ['fetchCampaignMembers', () => service.fetchCampaignMembers('4')],
    ['assignMemberRole', () => service.assignMemberRole('4', 'user-kyra', 'player')],
    ['createCampaignInvite', () => service.createCampaignInvite('4', 'player')],
    ['removeCampaignMember', () => service.removeCampaignMember('4', 'user-kyra')],
    ['fetchCampaignSessions', () => service.fetchCampaignSessions('4')],
    ['fetchSession', () => service.fetchSession('session-tomb-14')],
    ['fetchCharacters', () => service.fetchCharacters()],
    ['fetchCharacter', () => service.fetchCharacter('char-valeros')],
    ['modifyCharacterHealth', () => service.modifyCharacterHealth('char-valeros', -4)],
    ['createCharacter', () => service.createCharacter({ name: 'X', characterClass: 'Fighter', level: 1, maxHp: 10, armorClass: 10, speed: 30 } as any)],
    ['assignCharacterCampaign', () => service.assignCharacterCampaign('char-valeros', '4')],
    ['deleteCharacter', () => service.deleteCharacter('char-valeros')],
    ['fetchLobbyState', () => service.fetchLobbyState('4', 'session-tomb-14')],
    ['fetchBoardState', () => service.fetchBoardState('session-tomb-14')],
    ['fetchBoardTokens', () => service.fetchBoardTokens('session-tomb-14')],
    ['createCampaignSession', () => service.createCampaignSession('4', { title: 'Session #16' })],
    ['createCampaign', () => service.createCampaign({ title: 'Ashen Keep' } as any)],
    ['updateCampaign', () => service.updateCampaign('4', { title: 'Renamed' } as any)],
    ['requestHotSwap', () => service.requestHotSwap('session-tomb-14', 'char-valeros', 'user-fixture')],
    ['fetchRosterCampaignOptions', () => service.fetchRosterCampaignOptions()],
  ];

  for (const [name, call] of calls) {
    it(`${name} returns { ok: false } with the server message`, async () => {
      const result = await call();
      assert.equal(result.ok, false, `${name} must fail when the gateway fails`);
      assert.equal((result as any).status, 500);
      assert.equal((result as any).message, 'boom');
      assert.equal('data' in result, false, `${name} must not carry data on failure`);
    });
  }

  it('does not change a campaign list after a failed create', async () => {
    const before = await service.fetchCampaigns();
    const created = await service.createCampaign({ title: 'Ashen Keep' } as any);
    const after = await service.fetchCampaigns();
    assert.equal(created.ok, false);
    assert.deepEqual(after, before);
  });

  it('does not add a character after a failed create', async () => {
    const created = await service.createCharacter({ name: 'Ghost' } as any);
    assert.equal(created.ok, false);
    const roster = await service.fetchCharacters();
    assert.equal(roster.ok, false);
  });

  it('reports network failure as status 0 with a readable message', async () => {
    gateway.restore();
    globalThis.fetch = (async () => { throw new TypeError('connection refused'); }) as typeof fetch;
    try {
      const result = await service.fetchCampaigns();
      assert.equal(result.ok, false);
      assert.equal((result as any).status, 0);
      assert.match((result as any).message, /gateway could not be reached/);
    } finally {
      gateway = installFakeGateway({});
    }
  });
});
