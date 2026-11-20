/**
 * The session view reads the caller's own seat, with its stand-in state (TASK-0974).
 *
 * game_session holds the stand-in state on the session participant. The session load reads the
 * session state on every load and keeps each seated participant. A `player_stand_in` frame
 * updates the seat. Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 * Hard Invariant 7: the gateway is faked at the fetch boundary only.
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { loadActiveSessionData } from '../../src/app/session-data-loader.ts';
import { handleSessionMessage } from '../../src/app/session-messages.ts';
import { findCallerSeat } from '../../src/app/active-character.ts';
import type { MatchedRoute } from '../../src/router/index.ts';
import type { RunefobleApp } from '../../src/runefoble-app.ts';
import { installFakeGateway, type FakeGateway, type GatewayRoute } from '../support/fake-gateway.ts';
import { FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS } from '../support/app-data-service.fixtures.ts';
import { OWNER_BOARD_STATE, OWNER_PARTICIPANTS, OWNER_SESSION_STATE } from '../support/owner-wire-fixtures.ts';

const ROUTE = { params: { campaignId: '4', sessionId: 'session-tomb-14' } } as unknown as MatchedRoute;
const SESSION_PATH = 'GET /api/v1/sessions/session-tomb-14';

/** The session state with one participant's stand-in flag set. */
function stateWithStandIn(playerId: string, active: boolean): Record<string, unknown> {
  const entry = { ...OWNER_PARTICIPANTS[playerId as keyof typeof OWNER_PARTICIPANTS], is_stand_in_active: active };
  return { ...OWNER_SESSION_STATE, participants: { ...OWNER_PARTICIPANTS, [playerId]: entry } };
}

function installLoadGateway(session: GatewayRoute): FakeGateway {
  return installFakeGateway({
    'GET /api/v1/boards/session-tomb-14': { body: OWNER_BOARD_STATE },
    [SESSION_PATH]: session,
    'GET /api/v1/sessions/session-tomb-14/events': { body: [] },
    'GET /api/v1/characters': { body: FALLBACK_CHARACTERS },
    'GET /api/v1/campaigns/4': { body: FALLBACK_CAMPAIGNS[0] },
    'GET /api/v1/campaigns/4/capabilities': { body: { manage: false, run_session: false, play: true, view: true } },
  });
}

function newHost(currentUserId: string): RunefobleApp {
  return {
    characters: [], events: [], tokens: [], loadError: null, currentUserId,
    boardKind: 'loading', sessionSeats: [], sessionParticipants: [], boardCols: 10, boardRows: 10,
    sessionTitle: 'Session', currentCampaign: null, campaignCapabilities: null,
    resolveActiveCharacter: () => null, lobbyParticipants: [],
  } as unknown as RunefobleApp;
}

describe('The session load reads the caller seat on every load (TASK-0974)', () => {
  let gateway: FakeGateway | undefined;
  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('keeps the caller seat with its character and its stand-in state', async () => {
    gateway = installLoadGateway({ body: stateWithStandIn('user-fixture', true) });
    const host = newHost('user-fixture');

    await loadActiveSessionData(host, ROUTE);

    assert.deepEqual(host.sessionParticipants.find((p) => p.userId === 'user-fixture'), {
      userId: 'user-fixture', characterId: 'char-valeros', characterName: 'Valeros of Korvosa', isStandInActive: true,
    });
    assert.equal(findCallerSeat(host.sessionParticipants, 'user-fixture')?.isStandInActive, true);
  });

  it('reads the stand-in state again on a later load, so a released stand-in clears', async () => {
    let active = true;
    gateway = installLoadGateway(() => ({ body: stateWithStandIn('user-fixture', active) }));
    const host = newHost('user-fixture');

    await loadActiveSessionData(host, ROUTE);
    assert.equal(findCallerSeat(host.sessionParticipants, 'user-fixture')?.isStandInActive, true);

    active = false;
    await loadActiveSessionData(host, ROUTE);
    assert.equal(findCallerSeat(host.sessionParticipants, 'user-fixture')?.isStandInActive, false);
  });

  it('gives a player with no seat no caller seat, and keeps the other seats', async () => {
    gateway = installLoadGateway({ body: OWNER_SESSION_STATE });
    const host = newHost('user-stranger');

    await loadActiveSessionData(host, ROUTE);

    assert.equal(findCallerSeat(host.sessionParticipants, 'user-stranger'), null);
    assert.deepEqual(host.sessionParticipants.map((p) => p.userId), ['user-fixture', 'user-kyra']);
  });

  it('fails the load when the session state has a participant without is_stand_in_active', async () => {
    const broken = { ...OWNER_SESSION_STATE, participants: { 'user-fixture': { ...OWNER_PARTICIPANTS['user-fixture'], is_stand_in_active: undefined } } };
    gateway = installLoadGateway({ body: broken });
    const host = newHost('user-fixture');

    await loadActiveSessionData(host, ROUTE);

    assert.equal(host.loadError?.status, 502);
    assert.match(host.loadError?.message ?? '', /is_stand_in_active/);
  });
});

describe('A player_stand_in frame updates the caller seat (TASK-0974)', () => {
  it('sets the stand-in state of the seat that the frame names', () => {
    const host = newHost('user-fixture');
    host.sessionParticipants = [
      { userId: 'user-fixture', characterId: 'char-valeros', characterName: 'Valeros', isStandInActive: false },
      { userId: 'user-kyra', characterId: 'char-kyra', characterName: 'Kyra', isStandInActive: false },
    ];
    host.lobbyParticipants = [];

    handleSessionMessage(host, { type: 'player_stand_in', userId: 'user-fixture', isAbsent: true });

    assert.equal(findCallerSeat(host.sessionParticipants, 'user-fixture')?.isStandInActive, true);
    assert.equal(host.sessionParticipants.find((p) => p.userId === 'user-kyra')?.isStandInActive, false);
  });
});
