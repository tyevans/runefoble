/**
 * Unit & Integration tests for Unified Campaign Detail View Orchestration and Tabbed Navigation.
 * TASK-0250: Unified Campaign Detail View Orchestration and Tabbed Navigation
 * ADR-0004, ADR-0007, ADR-0012, ADR-0013, PRD-0023, US-0064, US-0067
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router, type MatchedRoute } from '../src/router/router.ts';
import { AppDataService } from '../src/services/app-data-service.ts';
import type { AppActiveView } from '../src/runefoble-app.ts';
import type { UpdateCampaignPayload } from '@runefoble/game-session-ui';

function resolveAppActiveView(route: MatchedRoute | null): AppActiveView {
  const pat = route?.pattern || '';
  if (pat === '#/login' || pat === '#/register') return 'login';
  if (pat.startsWith('#/campaigns/:campaignId/lobby/')) return 'session-lobby';
  if (pat.startsWith('#/campaigns/:campaignId/sessions/')) return 'session-active';
  if (pat === '#/campaigns/:campaignId/characters') return 'campaign-characters';
  if (pat === '#/campaigns/:campaignId/codex') return 'campaign-codex';
  if (pat === '#/campaigns/:campaignId/analytics') return 'campaign-analytics';
  if (pat.startsWith('#/campaigns/:campaignId')) return 'campaign-detail';
  if (pat === '#/characters') return 'characters';
  return pat === '#/profile' ? 'profile' : 'campaigns';
}

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
    assert.equal(resolveAppActiveView(detailRoute), 'campaign-detail');
    assert.equal(detailRoute?.params.campaignId, '4');

    const partyRoute = router.match('#/campaigns/4/characters');
    assert.equal(resolveAppActiveView(partyRoute), 'campaign-characters');
    assert.equal(partyRoute?.params.campaignId, '4');
  });

  it('disambiguates #/campaigns/:id/codex as campaign-codex and #/campaigns/:id/analytics as campaign-analytics (TASK-0355)', () => {
    const codexRoute = router.match('#/campaigns/4/codex');
    assert.equal(resolveAppActiveView(codexRoute), 'campaign-codex');
    assert.equal(codexRoute?.params.campaignId, '4');

    const analyticsRoute = router.match('#/campaigns/4/analytics');
    assert.equal(resolveAppActiveView(analyticsRoute), 'campaign-analytics');
    assert.equal(analyticsRoute?.params.campaignId, '4');
  });

  it('disambiguates #/profile as profile view', () => {
    const profileRoute = router.match('#/profile');
    assert.equal(resolveAppActiveView(profileRoute), 'profile');
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
    assert.equal(resolveAppActiveView(router.getCurrentRoute()), 'campaign-detail');

    await router.navigate('#/campaigns/4/characters');
    assert.equal(resolveAppActiveView(router.getCurrentRoute()), 'campaign-characters');

    await router.navigate('#/campaigns/4/codex');
    assert.equal(resolveAppActiveView(router.getCurrentRoute()), 'campaign-codex');

    await router.navigate('#/campaigns/4/analytics');
    assert.equal(resolveAppActiveView(router.getCurrentRoute()), 'campaign-analytics');

    await router.navigate('#/campaigns/4');
    assert.equal(resolveAppActiveView(router.getCurrentRoute()), 'campaign-detail');

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

  beforeEach(() => {
    dataService = new AppDataService();
  });

  it('fetches full campaign record including metadata and roles', async () => {
    const campaign = await dataService.fetchCampaign('4');
    assert.ok(campaign);
    assert.equal(campaign?.id, '4');
    assert.equal(campaign?.title, 'Tomb of the Star-Eater');
    assert.equal(campaign?.setting, 'Spelljammer Astral Void');
    assert.equal(campaign?.system, '5e');
    assert.equal(campaign?.role, 'owner');
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
    assert.ok(updated);
    assert.equal(updated?.title, 'Tomb of the Astral Colossus');
    assert.equal(updated?.setting, 'Deep Astral Sea');
    assert.equal(updated?.description, 'The ancient colossus awakes from cosmic slumber.');

    const reFetched = await dataService.fetchCampaign('4');
    assert.equal(reFetched?.title, 'Tomb of the Astral Colossus');
  });

  it('filters party characters scoped to active campaign', async () => {
    const characters = await dataService.fetchCharacters();
    const campaign4Characters = characters.filter((c) => c.campaignId === '4');

    assert.ok(campaign4Characters.length >= 2);
    assert.ok(campaign4Characters.some((c) => c.name.includes('Valeros')));
    assert.ok(campaign4Characters.some((c) => c.name.includes('Kyra')));
    assert.ok(!campaign4Characters.some((c) => c.name.includes('Ezren')));
  });
});

describe('Campaign Members Roster Lifecycle & Scoping (TASK-0353)', () => {
  let dataService: AppDataService;

  beforeEach(() => {
    dataService = new AppDataService();
  });

  it('returns distinct, campaign-scoped member rosters', async () => {
    const campaign4Members = await dataService.fetchCampaignMembers('4');
    assert.equal(campaign4Members.length, 3);
    assert.ok(campaign4Members.some((m) => m.user_id === 'user-valeros'));
    assert.ok(campaign4Members.some((m) => m.user_id === 'user-kyra'));
    assert.ok(campaign4Members.some((m) => m.user_id === 'user-merisiel'));

    const customMembers = await dataService.fetchCampaignMembers('camp-test-isolated');
    assert.equal(customMembers.length, 1);
    assert.equal(customMembers[0].role, 'owner');
    assert.ok(!customMembers.some((m) => m.user_id === 'user-kyra'));
  });

  it('assigns member role and updates the member list without reloading', async () => {
    await dataService.assignMemberRole('4', 'user-kyra', 'dungeon_master');
    const members = await dataService.fetchCampaignMembers('4');
    const kyra = members.find((m) => m.user_id === 'user-kyra');
    assert.ok(kyra);
    assert.equal(kyra?.role, 'dungeon_master');
  });

  it('generates a shareable campaign invite token and url', async () => {
    const invite = await dataService.createCampaignInvite('4', 'player', 48, 5);
    assert.ok(invite.token);
    assert.equal(invite.campaign_id, '4');
    assert.equal(invite.role, 'player');
    assert.ok(invite.invite_url.includes(invite.token));
    assert.equal(invite.max_uses, 5);
  });

  it('removes a member from the campaign roster', async () => {
    const before = await dataService.fetchCampaignMembers('4');
    assert.ok(before.some((m) => m.user_id === 'user-merisiel'));

    await dataService.removeCampaignMember('4', 'user-merisiel');
    const after = await dataService.fetchCampaignMembers('4');
    assert.ok(!after.some((m) => m.user_id === 'user-merisiel'));
  });
});

