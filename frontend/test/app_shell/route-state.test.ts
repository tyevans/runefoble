/**
 * App Shell Route State Test Suite (TASK-0642).
 *
 * Campaign, session, and character state come from the route and from gateway reads.
 * No fixture campaign, session, character, or stat may appear in the App Shell state.
 * The gateway is the only fake: it sits at the fetch boundary (Hard Invariant 7).
 * Governing ADRs: ADR-0004, ADR-0013.
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router, type MatchedRoute } from '../../src/router/router.ts';
import { loadRouteData } from '../../src/app/data-loader.ts';
import { selectCharacterFromEvent } from '../../src/app/character-actions.ts';
import { pickActiveCharacter } from '../../src/app/active-character.ts';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';
import type { RunefobleApp } from '../../src/runefoble-app.ts';

const HARBOUR = { id: 'harbour-watch', title: 'Harbour Watch', role: 'owner', permissions: { view: true, manage: true, invite: true, launch_session: true, assign_roles: true } };
const GLASS = { id: 'glass-crypt', title: 'Glass Crypt', role: 'owner', permissions: { view: true, manage: true, invite: true, launch_session: true, assign_roles: true } };

function routeFor(path: string): MatchedRoute {
  const route = new Router().match(path);
  assert.ok(route, `route ${path} must match`);
  return route;
}

/** A host with the App Shell state fields that the loaders read and write. */
function fakeHost(view: string, overrides: Record<string, unknown> = {}) {
  const host = {
    campaignId: '',
    sessionId: '',
    campaignTitle: '',
    sessionTitle: '',
    loadError: null as unknown,
    characters: [] as any[],
    campaigns: [] as any[],
    activeCharacter: null as any,
    selectedCharacter: null as any,
    selectedCharacterId: '',
    lobbyParticipants: [] as any[],
    currentUserId: 'user-signed-in',
    currentCampaign: null as any,
    campaignMembers: [] as any[],
    campaignSessions: [] as any[],
    rosterCampaigns: [] as any[],
    tokens: [] as any[],
    events: [] as any[],
    boardCols: 10,
    boardRows: 10,
    atmosphere: { location_name: '' },
    breadcrumbs: [] as any[],
    toasts: [] as string[],
    getActiveView: () => view,
    showToast(message: string) { this.toasts.push(message); },
    resolveActiveCharacter(campaignId: string) {
      if (this.activeCharacter) return this.activeCharacter;
      this.activeCharacter = pickActiveCharacter(this.characters, campaignId);
      return this.activeCharacter;
    },
    ...overrides,
  };
  return host as typeof host & RunefobleApp;
}

const EMPTY_LISTS = {
  'GET /api/v1/campaigns/glass-crypt/members': { body: [] },
  'GET /api/v1/campaigns/glass-crypt/sessions': { body: [] },
  'GET /api/v1/characters': { body: [] },
};

describe('App Shell Route State (TASK-0642)', () => {
  let gateway: FakeGateway;

  afterEach(() => gateway?.restore());

  it('loads the campaign named by the route, not a fixed campaign', async () => {
    gateway = installFakeGateway({
      ...EMPTY_LISTS,
      'GET /api/v1/campaigns/glass-crypt': { body: GLASS },
      'GET /api/v1/campaigns': { body: [HARBOUR, GLASS] },
    });
    const host = fakeHost('campaign-detail');

    await loadRouteData(host, routeFor('#/campaigns/glass-crypt'));

    assert.equal(host.campaignTitle, 'Glass Crypt');
    assert.equal(host.loadError, null);
    assert.ok(!gateway.calls.some((c) => c.path.includes('/campaigns/4')), 'no request may use the fixed campaign id 4');
  });

  it('lists every campaign from the API in the switcher on any routed view', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters': { body: [] },
      'GET /api/v1/campaigns': { body: [HARBOUR, GLASS] },
    });
    const host = fakeHost('characters');

    await loadRouteData(host, routeFor('#/characters'));

    assert.deepEqual(host.campaigns.map((c) => c.title), ['Harbour Watch', 'Glass Crypt']);
  });

  it('uses the session id from the route for session reads and never the fixed session', async () => {
    gateway = installFakeGateway({
      ...EMPTY_LISTS,
      'GET /api/v1/campaigns/glass-crypt': { body: GLASS },
      'GET /api/v1/campaigns': { body: [GLASS] },
    });
    const host = fakeHost('session-active');

    await loadRouteData(host, routeFor('#/campaigns/glass-crypt/sessions/sess-night-9'));

    assert.ok(gateway.calls.some((c) => c.path.includes('sess-night-9')), 'session reads must use the route session id');
    assert.ok(!gateway.calls.some((c) => c.path.includes('session-tomb-14')), 'no request may use the fixed session id');
  });

  it('returns no active character when the roster is empty, not a placeholder', () => {
    assert.equal(pickActiveCharacter([], 'glass-crypt'), null);
  });

  it('prefers the roster character assigned to the route campaign', () => {
    const roster = [
      { id: 'char-harbour', name: 'Mira', campaignId: 'harbour-watch' },
      { id: 'char-glass', name: 'Oren', campaignId: 'glass-crypt' },
    ] as any[];
    assert.equal(pickActiveCharacter(roster, 'glass-crypt')?.id, 'char-glass');
  });

  it('loads a selected character record and invents no stats', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters/char-new': { body: { id: 'char-new', name: 'Harsk the Ranger', characterClass: 'Ranger', level: 1 } },
    });
    const host = fakeHost('session-lobby');
    const event = new Event('select-character') as CustomEvent;
    Object.assign(event, { detail: { characterId: 'char-new', userId: 'user-signed-in' } });

    await selectCharacterFromEvent(host, event);

    assert.equal(host.activeCharacter?.name, 'Harsk the Ranger');
    assert.equal(host.activeCharacter?.currentHp, undefined, 'the App Shell must not invent current HP');
    assert.equal(host.activeCharacter?.armorClass, undefined, 'the App Shell must not invent armor class');
  });

  it('shows the data error when the selected character cannot be read', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters/char-missing': { status: 404, body: { detail: 'Character not found' } },
    });
    const host = fakeHost('session-lobby');
    const event = new Event('select-character') as CustomEvent;
    Object.assign(event, { detail: { characterId: 'char-missing', userId: 'user-signed-in' } });

    await selectCharacterFromEvent(host, event);

    assert.equal(host.activeCharacter, null);
    assert.equal((host.loadError as { status: number }).status, 404);
  });
});
