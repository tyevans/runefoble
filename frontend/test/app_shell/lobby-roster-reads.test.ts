/**
 * Lobby roster reads after seat frames (TASK-0974 follow-up).
 *
 * The lobby reads the roster at load and opens the socket at the same time. A frame for a seat
 * that the page does not have yet must not be lost: the lobby reads the roster again from the
 * owner. Other routes do not read the lobby roster. The gateway is the only fake (Hard Invariant 7).
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { handleSessionMessage } from '../../src/app/session-messages.ts';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';
import { OWNER_CAMPAIGN_MEMBERS, OWNER_PARTICIPANTS, OWNER_SESSION_STATE } from '../support/owner-wire-fixtures.ts';
import type { RunefobleApp } from '../../src/runefoble-app.ts';

const SESSION = 'session-tomb-14';
const LOBBY = { pattern: '#/campaigns/:campaignId/lobby/:sessionId' };
const ACTIVE = { pattern: '#/campaigns/:campaignId/sessions/:sessionId' };
const KYRA_ABSENT = { ...OWNER_SESSION_STATE, participants: { ...OWNER_PARTICIPANTS, 'user-kyra': { ...OWNER_PARTICIPANTS['user-kyra'], is_stand_in_active: true } } };

function newHost(route: unknown): RunefobleApp {
  return {
    campaignId: '4', sessionId: SESSION, currentRoute: route, currentUserId: 'user-fixture',
    lobbyParticipants: [], lobbyAvailableCharacters: [], sessionParticipants: [],
    showToast: () => undefined,
  } as unknown as RunefobleApp;
}

function installRosterGateway(): FakeGateway {
  return installFakeGateway({
    [`GET /api/v1/sessions/${SESSION}`]: { body: KYRA_ABSENT },
    'GET /api/v1/campaigns/4/members': { body: OWNER_CAMPAIGN_MEMBERS },
    'GET /api/v1/characters': { body: [] },
  });
}

async function settle(gateway: FakeGateway, reads: number): Promise<void> {
  for (let i = 0; i < 50 && gateway.calls.length < reads; i += 1) await new Promise((r) => setTimeout(r, 0));
  await new Promise((r) => setTimeout(r, 0));
}

describe('a seat frame in the lobby reads the roster again', () => {
  let gateway: FakeGateway | undefined;
  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('adds the seat that the page did not have when the stand-in frame came', async () => {
    gateway = installRosterGateway();
    const host = newHost(LOBBY);

    handleSessionMessage(host, { type: 'player_stand_in', userId: 'user-kyra', isAbsent: true });
    await settle(gateway, 3);

    const kyra = host.lobbyParticipants.find((p) => p.userId === 'user-kyra');
    assert.ok(kyra, 'the roster read must add the seat of Kyra');
    assert.equal(kyra.isAbsent, true);
  });

  it('reads the roster after a readiness frame too', async () => {
    gateway = installRosterGateway();
    const host = newHost(LOBBY);

    handleSessionMessage(host, { type: 'player_readiness', userId: 'user-kyra', isReady: true });
    await settle(gateway, 3);

    assert.equal(host.lobbyParticipants.length, 2);
  });

  it('does not read the lobby roster on the session route', async () => {
    gateway = installRosterGateway();
    const host = newHost(ACTIVE);

    handleSessionMessage(host, { type: 'player_stand_in', userId: 'user-kyra', isAbsent: true });
    await settle(gateway, 1);

    assert.equal(gateway.calls.length, 0);
  });
});
