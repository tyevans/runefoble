/**
 * View controller tests (TASK-0643).
 * Each controller renders its view and loads its data through the public registry.
 * The gateway is the only fake, at the fetch boundary.
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router } from '../src/router/router.ts';
import { VIEW_CONTROLLERS } from '../src/views/index.ts';
import { loadRouteData } from '../src/app/data-loader.ts';
import { launchSession } from '../src/app/session-actions.ts';
import type { AppActiveView } from '../src/router/view-resolver.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

const templateText = (t: { strings: TemplateStringsArray }) => t.strings.join('');

function host(view: AppActiveView, extra: Record<string, unknown> = {}): any {
  return {
    campaignId: 'c1', sessionId: 's1', campaigns: [], characters: [], loadError: null, toasts: [] as string[],
    campaignMembers: [], campaignSessions: [], rosterCampaigns: [], routeParams: {}, activeCharacter: null,
    sessionSocket: { current: null }, selectedCharacter: null, selectedCharacterId: '', breadcrumbs: [],
    getActiveView: () => view,
    showToast(m: string) { this.toasts.push(m); },
    ...extra,
  };
}

describe('view controllers render', () => {
  const cases: Array<[AppActiveView, string]> = [
    ['login', 'Authentication Portal'],
    ['campaigns', '<runefoble-campaign-dashboard'],
    ['campaign-detail', 'campaign-hub-layout'],
    ['characters', '<runefoble-character-roster'],
    ['session-lobby', '<runefoble-session-lobby'],
    ['profile', '<runefoble-user-profile'],
  ];
  for (const [view, marker] of cases) {
    it(`${view} renders its element`, () => {
      const out = VIEW_CONTROLLERS[view].render(host(view), view) as any;
      assert.ok(templateText(out).includes(marker));
    });
  }

  it('the character sheet view renders an empty state without a record', () => {
    const out = VIEW_CONTROLLERS['character-sheet'].render(host('character-sheet'), 'character-sheet') as any;
    assert.ok(templateText(out).includes('character-sheet-empty'));
  });
});

describe('view controllers load', () => {
  let gateway: FakeGateway;
  afterEach(() => gateway.restore());

  it('the dashboard loads campaigns and skips the switcher read', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/campaigns': { body: [{ id: 'c1', title: 'One', role: 'owner' }] } });
    const h = host('campaigns');
    await loadRouteData(h, new Router().match('#/campaigns')!);
    assert.equal(h.campaigns.length, 1);
    assert.equal(gateway.calls.length, 1);
  });

  it('a failed roster read sets the load error', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/characters': { status: 503, body: { detail: 'down' } }, '*': { status: 503, body: { detail: 'down' } } });
    const h = host('characters', { failures: [] });
    await loadRouteData(h, new Router().match('#/characters')!);
    assert.ok(h.loadError);
  });
});

describe('launchSession', () => {
  it('reports an unknown session as a toast', () => {
    const h = host('session-lobby', { campaignId: '', sessionId: '' });
    launchSession(h, new CustomEvent('launch-session'));
    assert.equal(h.toasts.length, 1);
  });
});
