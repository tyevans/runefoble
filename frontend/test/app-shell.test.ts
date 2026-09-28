/**
 * Unit & Integration tests for App Shell View Orchestration and Session Transition.
 * TASK-0213: App Shell View Orchestration and Session Transition
 * ADR-0004, ADR-0012, ADR-0013, PRD-0023, US-0065, US-0066
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router, type MatchedRoute } from '../src/router/router.ts';
import { AppDataService } from '../src/services/app-data-service.ts';
import type { AppActiveView } from '../src/runefoble-app.ts';

// Helper view resolver mimicking RunefobleApp.getActiveView()
function resolveActiveView(route: MatchedRoute | null): AppActiveView {
  const pat = route?.pattern || '';
  if (pat === '#/login' || pat === '#/register') return 'login';
  if (pat.startsWith('#/campaigns/:campaignId/lobby/')) return 'session-lobby';
  if (pat.startsWith('#/campaigns/:campaignId/sessions/')) return 'session-active';
  if (pat === '#/campaigns/:campaignId/characters') return 'campaign-characters';
  if (pat.startsWith('#/campaigns/:campaignId')) return 'campaign-detail';
  if (pat === '#/characters') return 'characters';
  return pat === '#/profile' ? 'profile' : 'campaigns';
}

// Helper checking if a route requires an active session WebSocket
function isSessionWebSocketRequired(route: MatchedRoute | null): boolean {
  const pat = route?.pattern || '';
  return pat === '#/campaigns/:campaignId/sessions/:sessionId' ||
         pat === '#/campaigns/:campaignId/lobby/:sessionId';
}

describe('App Shell Dynamic View Routing & Parameter Extraction', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('resolves login and registration views with auth modal trigger', () => {
    const loginRoute = router.match('#/login');
    assert.equal(resolveActiveView(loginRoute), 'login');

    const registerRoute = router.match('#/register');
    assert.equal(resolveActiveView(registerRoute), 'login');
  });

  it('resolves campaign dashboard view for root campaigns route', () => {
    const route = router.match('#/campaigns');
    assert.equal(resolveActiveView(route), 'campaigns');
  });

  it('resolves campaign detail view with extracted campaignId parameter', () => {
    const route = router.match('#/campaigns/4');
    assert.equal(resolveActiveView(route), 'campaign-detail');
    assert.equal(route?.params.campaignId, '4');

    const partyRoute = router.match('#/campaigns/42/characters');
    assert.equal(resolveActiveView(partyRoute), 'campaign-characters');
    assert.equal(partyRoute?.params.campaignId, '42');

    const profileRoute = router.match('#/profile');
    assert.equal(resolveActiveView(profileRoute), 'profile');
  });

  it('resolves character roster view for #/characters', () => {
    const route = router.match('#/characters');
    assert.equal(resolveActiveView(route), 'characters');
  });

  it('resolves session lobby view for #/campaigns/:id/lobby/:sessionId', () => {
    const route = router.match('#/campaigns/4/lobby/session-tomb-14');
    assert.equal(resolveActiveView(route), 'session-lobby');
    assert.equal(route?.params.campaignId, '4');
    assert.equal(route?.params.sessionId, 'session-tomb-14');
  });

  it('resolves active VTT session view for #/campaigns/:id/sessions/:sessionId', () => {
    const route = router.match('#/campaigns/4/sessions/session-tomb-14');
    assert.equal(resolveActiveView(route), 'session-active');
    assert.equal(route?.params.campaignId, '4');
    assert.equal(route?.params.sessionId, 'session-tomb-14');
  });

  it('defaults to campaigns view for empty or unrecognized route', () => {
    const emptyRoute = router.match('');
    assert.equal(resolveActiveView(emptyRoute), 'campaigns');

    const unknownRoute = router.match('#/unknown-route');
    assert.equal(resolveActiveView(unknownRoute), 'campaigns');
  });
});

describe('Route-Bound WebSocket Lifecycle Management', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('activates WebSocket only on session-lobby and session-active routes', () => {
    assert.equal(isSessionWebSocketRequired(router.match('#/campaigns')), false);
    assert.equal(isSessionWebSocketRequired(router.match('#/campaigns/4')), false);
    assert.equal(isSessionWebSocketRequired(router.match('#/characters')), false);
    assert.equal(isSessionWebSocketRequired(router.match('#/login')), false);

    assert.equal(isSessionWebSocketRequired(router.match('#/campaigns/4/lobby/sess-1')), true);
    assert.equal(isSessionWebSocketRequired(router.match('#/campaigns/4/sessions/sess-1')), true);
  });

  it('tears down WebSocket when navigating away from an active session', async () => {
    let wsDisconnected = false;
    let connectedSessionId: string | null = null;

    // Simulate App Shell lifecycle handlers
    const connectWS = (sessionId: string) => {
      connectedSessionId = sessionId;
      wsDisconnected = false;
    };
    const disconnectWS = () => {
      connectedSessionId = null;
      wsDisconnected = true;
    };

    router.onRouteChanged((route) => {
      if (isSessionWebSocketRequired(route)) {
        connectWS(route.params.sessionId);
      } else {
        disconnectWS();
      }
    });

    // Navigate to active session
    await router.navigate('#/campaigns/4/sessions/sess-100');
    assert.equal(connectedSessionId, 'sess-100');
    assert.equal(wsDisconnected, false);

    // Navigate to campaign dashboard
    await router.navigate('#/campaigns');
    assert.equal(connectedSessionId, null);
    assert.equal(wsDisconnected, true);
  });

  it('switches WebSocket connection when switching directly between sessions', async () => {
    const connections: string[] = [];

    router.onRouteChanged((route) => {
      if (isSessionWebSocketRequired(route)) {
        connections.push(route.params.sessionId);
      }
    });

    await router.navigate('#/campaigns/4/lobby/sess-A');
    await router.navigate('#/campaigns/5/sessions/sess-B');

    assert.deepEqual(connections, ['sess-A', 'sess-B']);
  });
});

describe('Session Start Transition (US-0065 & PRD-0023)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('transitions router from lobby to active VTT on launch-session event', async () => {
    await router.navigate('#/campaigns/4/lobby/session-tomb-14');
    assert.equal(router.getCurrentRoute()?.pattern, '#/campaigns/:campaignId/lobby/:sessionId');

    // Simulate dispatching launch-session event from <runefoble-session-lobby>
    const campaignId = '4';
    const sessionId = 'session-tomb-14';
    await router.navigate(`#/campaigns/${campaignId}/sessions/${sessionId}`);

    const targetRoute = router.getCurrentRoute();
    assert.equal(targetRoute?.pattern, '#/campaigns/:campaignId/sessions/:sessionId');
    assert.equal(targetRoute?.params.campaignId, '4');
    assert.equal(targetRoute?.params.sessionId, 'session-tomb-14');
    assert.equal(resolveActiveView(targetRoute), 'session-active');
  });

  it('transitions router from lobby to active VTT upon incoming WebSocket session_started message', async () => {
    await router.navigate('#/campaigns/4/lobby/session-tomb-14');

    // Simulate incoming WS message
    const wsMessage = {
      type: 'session_started',
      campaignId: '4',
      sessionId: 'session-tomb-14',
    };

    if (wsMessage.type === 'session_started') {
      await router.navigate(`#/campaigns/${wsMessage.campaignId}/sessions/${wsMessage.sessionId}`);
    }

    assert.equal(router.getCurrentRoute()?.pattern, '#/campaigns/:campaignId/sessions/:sessionId');
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns/4/sessions/session-tomb-14');
  });
});

describe('Route-Parameterized AppDataService Data Fetching', () => {
  let dataService: AppDataService;

  beforeEach(() => {
    dataService = new AppDataService();
  });

  it('fetches campaign list with fallback defaults', async () => {
    const campaigns = await dataService.fetchCampaigns();
    assert.ok(Array.isArray(campaigns));
    assert.ok(campaigns.length >= 2);
    assert.equal(campaigns[0].id, '4');
    assert.equal(campaigns[0].title, 'Tomb of the Star-Eater');
  });

  it('fetches specific campaign details parameterized by campaignId', async () => {
    const campaign4 = await dataService.fetchCampaign('4');
    assert.ok(campaign4);
    assert.equal(campaign4?.id, '4');
    assert.equal(campaign4?.title, 'Tomb of the Star-Eater');

    const campaign5 = await dataService.fetchCampaign('5');
    assert.ok(campaign5);
    assert.equal(campaign5?.id, '5');
    assert.equal(campaign5?.title, 'Whispering Depths');
  });

  it('fetches campaign members for specific campaignId', async () => {
    const members = await dataService.fetchCampaignMembers('4');
    assert.ok(Array.isArray(members));
    assert.ok(members.length > 0);
    assert.ok(members.some((m) => m.role === 'owner'));
  });

  it('fetches campaign sessions for specific campaignId', async () => {
    const sessions = await dataService.fetchCampaignSessions('4');
    assert.ok(Array.isArray(sessions));
    assert.ok(sessions.length >= 2);
    assert.ok(sessions.some((s) => s.status === 'active'));
    assert.ok(sessions.some((s) => s.status === 'lobby'));
  });

  it('fetches lobby state for specific sessionId', async () => {
    const lobby = await dataService.fetchLobbyState('session-tomb-14');
    assert.ok(lobby.participants);
    assert.ok(lobby.availableCharacters);
    assert.ok(lobby.participants.some((p) => p.isReady));
  });

  it('fetches board tokens for active session', async () => {
    const tokens = await dataService.fetchBoardTokens('session-tomb-14');
    assert.ok(Array.isArray(tokens));
    assert.ok(tokens.length >= 4);
    assert.ok(tokens.some((t) => t.name === 'Valeros'));
    assert.ok(tokens.some((t) => t.isAiControlled));
  });

  it('creates character via createCharacter mutation', async () => {
    const newChar = await dataService.createCharacter({
      name: 'Harsk the Ranger',
      characterClass: 'Ranger',
      level: 3,
      maxHp: 28,
      armorClass: 15,
      speed: 30,
      abilityScores: { str: 14, dex: 16, con: 14, int: 10, wis: 14, cha: 8 },
      portraitUrl: '/assets/portraits/ranger.svg',
    });
    assert.ok(newChar.id);
    assert.equal(newChar.name, 'Harsk the Ranger');
    assert.equal(newChar.characterClass, 'Ranger');
    const all = await dataService.fetchCharacters();
    assert.ok(all.some((c) => c.name === 'Harsk the Ranger'));
  });

  it('assigns character to campaign and unassigns via assignCharacterCampaign', async () => {
    // Pick an existing character
    const chars = await dataService.fetchCharacters();
    const ezren = chars.find((c) => c.id === 'char-ezren') || chars[0];
    assert.ok(ezren);

    // Assign to campaign 4
    await dataService.assignCharacterCampaign(ezren.id, '4');
    let updatedChars = await dataService.fetchCharacters();
    let updated = updatedChars.find((c) => c.id === ezren.id);
    assert.equal(updated?.campaignId, '4');
    assert.equal(updated?.campaignTitle, 'Tomb of the Star-Eater');

    // Unassign from campaign
    await dataService.assignCharacterCampaign(ezren.id, null);
    updatedChars = await dataService.fetchCharacters();
    updated = updatedChars.find((c) => c.id === ezren.id);
    assert.equal(updated?.campaignId, null);
  });

  it('deletes character via deleteCharacter mutation', async () => {
    const created = await dataService.createCharacter({
      name: 'Temp Deletable',
      characterClass: 'Fighter',
      level: 1,
      maxHp: 10,
      armorClass: 10,
      speed: 30,
      abilityScores: { str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 },
      portraitUrl: '',
    });
    let list = await dataService.fetchCharacters();
    assert.ok(list.some((c) => c.id === created.id));

    await dataService.deleteCharacter(created.id);
    list = await dataService.fetchCharacters();
    assert.ok(!list.some((c) => c.id === created.id));
  });
});

describe('Character Roster Inspect Navigation (TASK-0254 & US-0069)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('navigates to deep route #/characters/:characterId on inspect sheet event', async () => {
    await router.navigate('#/characters');
    assert.equal(router.getCurrentRoute()?.path, '#/characters');

    // Inspect character event triggers navigation
    const targetCharacterId = 'char-valeros';
    await router.navigate(`#/characters/${targetCharacterId}`);

    const route = router.getCurrentRoute();
    assert.equal(route?.path, '#/characters/char-valeros');
  });
});
