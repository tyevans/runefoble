/**
 * Unit & Integration tests for Unified Campaign Detail View Orchestration and Tabbed Navigation.
 * TASK-0250: Unified Campaign Detail View Orchestration and Tabbed Navigation
 * ADR-0004, ADR-0007, ADR-0012, ADR-0013, PRD-0023, US-0064, US-0067
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router, type MatchedRoute } from '../src/router/router.ts';
import { AppDataService } from '../src/services/app-data-service.ts';
import { resolveActiveView, type AppActiveView } from '../src/router/view-resolver.ts';
import type { UpdateCampaignPayload } from '@runefoble/game-session-ui';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';
import { FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS, FALLBACK_MEMBERS } from './support/app-data-service.fixtures.ts';

describe('Campaign Detail Sub-View Disambiguation (TASK-0250)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
    router.setTitleResolver((type, id) => {
      if (type === 'campaign' && id === '4') return 'Tomb of the Star-Eater';
      return undefined;
    });
  });

  it('disambiguates #/campaigns/:id as campaign-detail and #/campaigns/:id/characters as campaign-characters', () => {
    const detailRoute = router.match('#/campaigns/4');
    assert.equal(resolveActiveView(detailRoute), 'campaign-detail');
    assert.equal(detailRoute?.params.campaignId, '4');

    const partyRoute = router.match('#/campaigns/4/characters');
    assert.equal(resolveActiveView(partyRoute), 'campaign-characters');
    assert.equal(partyRoute?.params.campaignId, '4');
  });

  it('disambiguates #/campaigns/:id/codex as campaign-codex and #/campaigns/:id/analytics as campaign-analytics (TASK-0355)', () => {
    const codexRoute = router.match('#/campaigns/4/codex');
    assert.equal(resolveActiveView(codexRoute), 'campaign-codex');
    assert.equal(codexRoute?.params.campaignId, '4');

    const analyticsRoute = router.match('#/campaigns/4/analytics');
    assert.equal(resolveActiveView(analyticsRoute), 'campaign-analytics');
    assert.equal(analyticsRoute?.params.campaignId, '4');
  });

  it('disambiguates #/profile as profile view', () => {
    const profileRoute = router.match('#/profile');
    assert.equal(resolveActiveView(profileRoute), 'profile');
  });

  it('generates accurate breadcrumbs across campaign detail tabs', () => {
    const detailRoute = router.match('#/campaigns/4');
    assert.ok(detailRoute);
    assert.equal(detailRoute.breadcrumbs.length, 2);
    assert.equal(detailRoute.breadcrumbs[0].label, 'Campaigns');
    assert.equal(detailRoute.breadcrumbs[1].label, 'Tomb of the Star-Eater');

    const partyRoute = router.match('#/campaigns/4/characters');
    assert.ok(partyRoute);
    assert.equal(partyRoute.breadcrumbs.length, 3);
    assert.equal(partyRoute.breadcrumbs[0].label, 'Campaigns');
    assert.equal(partyRoute.breadcrumbs[1].label, 'Tomb of the Star-Eater');
    assert.equal(partyRoute.breadcrumbs[2].label, 'Party');

    const codexRoute = router.match('#/campaigns/4/codex');
    assert.ok(codexRoute);
    assert.equal(codexRoute.breadcrumbs.length, 3);
    assert.equal(codexRoute.breadcrumbs[0].label, 'Campaigns');
    assert.equal(codexRoute.breadcrumbs[1].label, 'Tomb of the Star-Eater');
    assert.equal(codexRoute.breadcrumbs[2].label, 'Codex & Atlas');

    const analyticsRoute = router.match('#/campaigns/4/analytics');
    assert.ok(analyticsRoute);
    assert.equal(analyticsRoute.breadcrumbs.length, 3);
    assert.equal(analyticsRoute.breadcrumbs[0].label, 'Campaigns');
    assert.equal(analyticsRoute.breadcrumbs[1].label, 'Tomb of the Star-Eater');
    assert.equal(analyticsRoute.breadcrumbs[2].label, 'Chronicle & Stats');
  });

  it('switches between campaign tabs without page reloads', async () => {
    const routeChanges: string[] = [];
    router.onRouteChanged((route) => {
      routeChanges.push(route.path);
    });

    await router.navigate('#/campaigns/4');
    assert.equal(resolveActiveView(router.getCurrentRoute()), 'campaign-detail');

    await router.navigate('#/campaigns/4/characters');
    assert.equal(resolveActiveView(router.getCurrentRoute()), 'campaign-characters');

    await router.navigate('#/campaigns/4/codex');
    assert.equal(resolveActiveView(router.getCurrentRoute()), 'campaign-codex');

    await router.navigate('#/campaigns/4/analytics');
    assert.equal(resolveActiveView(router.getCurrentRoute()), 'campaign-analytics');

    await router.navigate('#/campaigns/4');
    assert.equal(resolveActiveView(router.getCurrentRoute()), 'campaign-detail');

    assert.deepEqual(routeChanges, [
      '#/campaigns/4',
      '#/campaigns/4/characters',
      '#/campaigns/4/codex',
      '#/campaigns/4/analytics',
      '#/campaigns/4',
    ]);
  });
});

describe('Campaign Metadata Loading & Update Flow (TASK-0250)', () => {
  let dataService: AppDataService;
  let gateway: FakeGateway;
  let campaign: any;

  beforeEach(() => {
    dataService = new AppDataService();
    campaign = { ...FALLBACK_CAMPAIGNS[0] };
    gateway = installFakeGateway({
      'GET /api/v1/campaigns/4': () => ({ body: campaign }),
      'PATCH /api/v1/campaigns/4': (req) => { campaign = { ...campaign, ...(req.body as any) }; return { body: campaign }; },
      'GET /api/v1/characters': { body: FALLBACK_CHARACTERS },
    });
  });

  afterEach(() => gateway.restore());

  it('fetches full campaign record including metadata and roles', async () => {
    const result = await dataService.fetchCampaign('4');
    assert.ok(result.ok);
    assert.equal(result.data.id, '4');
    assert.equal(result.data.title, 'Tomb of the Star-Eater');
    assert.equal(result.data.setting, 'Spelljammer Astral Void');
    assert.equal(result.data.system, '5e');
    assert.equal(result.data.role, 'owner');
  });

  it('updates campaign metadata via updateCampaign and retains updated values', async () => {
    const updatePayload: UpdateCampaignPayload = {
      campaignId: '4',
      title: 'Tomb of the Astral Colossus',
      setting: 'Deep Astral Sea',
      system: '5e',
      description: 'The ancient colossus awakes from cosmic slumber.',
    };

    const updated = await dataService.updateCampaign('4', updatePayload);
    assert.ok(updated.ok);
    assert.equal(updated.data.title, 'Tomb of the Astral Colossus');
    assert.equal(updated.data.setting, 'Deep Astral Sea');
    assert.equal(updated.data.description, 'The ancient colossus awakes from cosmic slumber.');

    const reFetched = await dataService.fetchCampaign('4');
    assert.ok(reFetched.ok);
    assert.equal(reFetched.data.title, 'Tomb of the Astral Colossus');
  });

  it('filters party characters scoped to active campaign', async () => {
    const characters = await dataService.fetchCharacters();
    assert.ok(characters.ok);
    const campaign4Characters = characters.data.filter((c) => c.campaignId === '4');

    assert.ok(campaign4Characters.length >= 2);
    assert.ok(campaign4Characters.some((c) => c.name.includes('Valeros')));
    assert.ok(campaign4Characters.some((c) => c.name.includes('Kyra')));
    assert.ok(!campaign4Characters.some((c) => c.name.includes('Ezren')));
  });
});

describe('Campaign Members Roster Lifecycle & Scoping (TASK-0353)', () => {
  let dataService: AppDataService;
  let gateway: FakeGateway;
  let members: any[];

  beforeEach(() => {
    dataService = new AppDataService();
    members = FALLBACK_MEMBERS.map((m) => ({ ...m }));
    gateway = installFakeGateway({
      'GET /api/v1/campaigns/4/members': () => ({ body: members }),
      'GET /api/v1/campaigns/camp-test-isolated/members': { body: [{ user_id: 'user-solo', username: 'Solo', role: 'owner' }] },
      'POST /api/v1/campaigns/4/roles': (req) => {
        const body = req.body as any;
        members.find((m) => m.user_id === body.user_id).role = body.role;
        return { status: 204 };
      },
      'POST /api/v1/campaigns/4/invites': (req) => ({
        status: 201,
        body: {
          token: 'inv-test-token', campaign_id: '4', role: (req.body as any).role, max_uses: (req.body as any).max_uses,
          invite_url: 'https://runefoble.local/#/join/inv-test-token', created_at: '2026-11-17T00:00:00Z',
        },
      }),
      'DELETE /api/v1/campaigns/4/members/user-merisiel': () => { members = members.filter((m) => m.user_id !== 'user-merisiel'); return { status: 204 }; },
    });
  });

  afterEach(() => gateway.restore());

  it('returns distinct, campaign-scoped member rosters', async () => {
    const campaign4Members = await dataService.fetchCampaignMembers('4');
    assert.ok(campaign4Members.ok);
    assert.equal(campaign4Members.data.length, 3);
    assert.ok(campaign4Members.data.some((m) => m.user_id === 'user-fixture'));
    assert.ok(campaign4Members.data.some((m) => m.user_id === 'user-kyra'));
    assert.ok(campaign4Members.data.some((m) => m.user_id === 'user-merisiel'));

    const customMembers = await dataService.fetchCampaignMembers('camp-test-isolated');
    assert.ok(customMembers.ok);
    assert.equal(customMembers.data.length, 1);
    assert.equal(customMembers.data[0].role, 'owner');
    assert.ok(!customMembers.data.some((m) => m.user_id === 'user-kyra'));
  });

  it('assigns member role and updates the member list without reloading', async () => {
    const assigned = await dataService.assignMemberRole('4', 'user-kyra', 'dungeon_master');
    assert.equal(assigned.ok, true);
    const after = await dataService.fetchCampaignMembers('4');
    assert.ok(after.ok);
    const kyra = after.data.find((m) => m.user_id === 'user-kyra');
    assert.ok(kyra);
    assert.equal(kyra.role, 'dungeon_master');
  });

  it('generates a shareable campaign invite token and url', async () => {
    const result = await dataService.createCampaignInvite('4', 'player', 48, 5);
    assert.ok(result.ok);
    const invite = result.data;
    assert.ok(invite.token);
    assert.equal(invite.campaign_id, '4');
    assert.equal(invite.role, 'player');
    assert.ok(invite.invite_url.includes(invite.token));
    assert.equal(invite.max_uses, 5);
  });

  it('removes a member from the campaign roster', async () => {
    const before = await dataService.fetchCampaignMembers('4');
    assert.ok(before.ok && before.data.some((m) => m.user_id === 'user-merisiel'));

    const removed = await dataService.removeCampaignMember('4', 'user-merisiel');
    assert.equal(removed.ok, true);
    const after = await dataService.fetchCampaignMembers('4');
    assert.ok(after.ok && !after.data.some((m) => m.user_id === 'user-merisiel'));
  });
});
