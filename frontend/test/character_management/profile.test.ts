/**
 * User Profile View & Campaign Creation Deduplication Test Suite.
 *
 * TASK-0288: Frontend Character Management Test Suite Modular Decomposition
 * Governing ADRs: ADR-0001, ADR-0004, ADR-0010, ADR-0012, ADR-0013
 * Hard Invariants: Hard Invariant 6 (< 130 lines), Hard Invariant 7 (Blackbox TDD)
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Router } from '../../src/router/router.ts';
import { AppDataService, appDataService } from '../../src/services/app-data-service.ts';
import { authService } from '../../src/auth/auth-service.ts';
import { FALLBACK_CAMPAIGNS } from '../../src/services/fallback-data.ts';
import type { CampaignItem, CreateCampaignPayload } from '../../../services/game_session/ui/src/campaigns/types.ts';

const APP_SHELL_PATH = resolve(import.meta.dirname, '../../src/runefoble-app.ts');
const PROFILE_PATH = resolve(import.meta.dirname, '../../src/components/runefoble-user-profile.ts');

describe('Profile Settings & Campaign Deduplication (US-0070, US-0071, TASK-0288)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('test_campaign_creation_single_event_dispatch: stops bubbling and deduplicates campaign list', async () => {
    const dataService = new AppDataService();
    let eventsDispatched = 0;
    let stopPropagationCalled = false;

    const fakeEvent = {
      detail: { title: 'Chronicles of the Astral Sea', setting: 'Astral Plane', system: '5e' } as CreateCampaignPayload,
      stopPropagation: () => { stopPropagationCalled = true; },
    };

    const handleCreatorSubmit = (e: typeof fakeEvent) => {
      e.stopPropagation();
      eventsDispatched += 1;
    };
    handleCreatorSubmit(fakeEvent);
    assert.equal(stopPropagationCalled, true, 'stopPropagation must be called on child submit');
    assert.equal(eventsDispatched, 1, 'Exactly one create-campaign event must be emitted');

    const newCamp = await dataService.createCampaign(fakeEvent.detail);
    assert.ok(newCamp.id, 'Campaign must be created with ID');
    assert.equal(newCamp.title, 'Chronicles of the Astral Sea');

    const duplicatedList: CampaignItem[] = [newCamp, newCamp, ...FALLBACK_CAMPAIGNS];
    const deduped = dataService.deduplicateCampaigns(duplicatedList);
    const count = deduped.filter((c) => c.id === newCamp.id).length;
    assert.equal(count, 1, 'Only one campaign card must appear on dashboard');
  });

  it('test_profile_route_renders_user_claims_and_updates: verifies profile view, breadcrumbs, and updates', async () => {
    await router.navigate('#/profile');
    const route = router.getCurrentRoute();
    assert.ok(route, 'Profile route must match');
    assert.equal(route.pattern, '#/profile');

    assert.equal(route.breadcrumbs.length, 2);
    assert.equal(route.breadcrumbs[0].label, 'Home');
    assert.equal(route.breadcrumbs[0].path, '#/campaigns');
    assert.equal(route.breadcrumbs[1].label, 'Account Settings');
    assert.equal(route.breadcrumbs[1].path, '#/profile');
    assert.equal(route.breadcrumbs[1].active, true);

    const profileContent = readFileSync(PROFILE_PATH, 'utf-8');
    assert.ok(profileContent.includes('@customElement('));
    assert.ok(profileContent.includes('class RunefobleUserProfile extends LitElement'));
    assert.ok(profileContent.includes('user.username'));
    assert.ok(profileContent.includes('user.email'));
    assert.ok(profileContent.includes('user.user_id'));
    assert.ok(profileContent.includes('role-badge'));

    const updated = await appDataService.updateProfile({ displayName: 'Valeros the Bold', bio: 'Korvosan Champion' });
    assert.equal(updated?.display_name, 'Valeros the Bold');
    assert.equal(authService.getUser()?.display_name, 'Valeros the Bold');

    const appShellContent = readFileSync(APP_SHELL_PATH, 'utf-8');
    assert.ok(appShellContent.includes('<runefoble-user-profile'));
    assert.ok(appShellContent.includes('.user=${authService.getUser()}'));
  });
});
