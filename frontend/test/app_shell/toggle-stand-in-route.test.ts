/**
 * Stand-in toggle and the stance drawer (TASK-0974 follow-up).
 *
 * A player who marks the seat absent in the lobby gets the stance drawer. A player who leaves the
 * lobby before the save answers must not get the drawer in the next view, because its backdrop
 * covers the session view. The gateway is the only fake (Hard Invariant 7).
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { toggleStandIn } from '../../src/app/session-actions.ts';
import { installFakeGateway, type FakeGateway, type GatewayRoute } from '../support/fake-gateway.ts';
import { OWNER_CAMPAIGN_MEMBERS, OWNER_SESSION_STATE } from '../support/owner-wire-fixtures.ts';

const SESSION = 'session-tomb-14';
const LOBBY = { pattern: '#/campaigns/:campaignId/sessions/:sessionId/lobby' };
const ACTIVE = { pattern: '#/campaigns/:campaignId/sessions/:sessionId' };
const CHARACTER = { id: 'char-valeros', name: 'Valeros', characterClass: 'Fighter', level: 3, owner_id: 'user-fixture', campaignId: '4' };

function makeHost() {
  return {
    sessionId: SESSION,
    campaignId: '4',
    currentUserId: 'user-fixture',
    currentRoute: LOBBY as unknown,
    activeCharacter: { id: CHARACTER.id, name: CHARACTER.name },
    sessionParticipants: [] as unknown[],
    lobbyParticipants: [] as unknown[],
    lobbyAvailableCharacters: [] as unknown[],
    absenteeStance: '',
    isAbsenteeDirectiveOpen: false,
    toasts: [] as string[],
    showToast(m: string) { this.toasts.push(m); },
  };
}

function routes(onStandIn: GatewayRoute): Record<string, GatewayRoute> {
  return {
    [`POST /api/v1/sessions/${SESSION}/seats/user-fixture/stand-in`]: onStandIn,
    [`GET /api/v1/sessions/${SESSION}`]: { body: OWNER_SESSION_STATE },
    'GET /api/v1/campaigns/4/members': { body: OWNER_CAMPAIGN_MEMBERS },
    'GET /api/v1/characters': { body: [CHARACTER] },
    [`GET /api/v1/characters/${CHARACTER.id}/guardrails`]: { body: { stance: 'cautious' } },
  };
}

function absentEvent() {
  return new CustomEvent('toggle-stand-in', { detail: { sessionId: SESSION, userId: 'user-fixture', isAbsent: true } });
}

describe('marking the own seat absent', () => {
  let gateway: FakeGateway | undefined;
  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('opens the stance drawer when the player stays in the lobby', async () => {
    gateway = installFakeGateway(routes({ body: {} }));
    const host = makeHost();

    await toggleStandIn(host as any, absentEvent() as any);

    assert.equal(host.isAbsenteeDirectiveOpen, true);
  });

  it('keeps the drawer closed when the player leaves the lobby before the save answers', async () => {
    const host = makeHost();
    gateway = installFakeGateway(routes(() => { host.currentRoute = ACTIVE; return { body: {} }; }));

    await toggleStandIn(host as any, absentEvent() as any);

    assert.equal(host.isAbsenteeDirectiveOpen, false);
  });
});
