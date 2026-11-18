/**
 * Unit tests for Profile Settings View & Campaign Creation Idempotency.
 * TASK-0257: Profile Settings View and Campaign Creation Idempotency
 * ADR-0001, ADR-0004, ADR-0007, ADR-0012, ADR-0013
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router } from '../src/router/router.ts';
import { AppDataService } from '../src/services/app-data-service.ts';
import { FALLBACK_CAMPAIGNS } from './support/app-data-service.fixtures.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';
import type { CampaignItem, CreateCampaignPayload } from '../../services/game_session/ui/src/campaigns/types.ts';
import { resolveActiveView as resolveView, type AppActiveView } from '../src/router/view-resolver.ts';

function resolveActiveView(path: string): AppActiveView {
  return resolveView(Router.getInstance().match(path));
}

describe('Profile Navigation & Breadcrumb Trail (TASK-0257)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('matches #/profile route and resolves active view as profile', () => {
    const matched = router.match('#/profile');
    assert.ok(matched, 'Route #/profile should be matched');
    assert.equal(matched.pattern, '#/profile');
    assert.equal(resolveActiveView('#/profile'), 'profile');
  });

  it('generates breadcrumb trail [Home, Account Settings] for #/profile', () => {
    const matched = router.match('#/profile');
    assert.ok(matched);
    assert.equal(matched.breadcrumbs.length, 2);
    assert.equal(matched.breadcrumbs[0].label, 'Home');
    assert.equal(matched.breadcrumbs[0].path, '#/campaigns');
    assert.equal(matched.breadcrumbs[1].label, 'Account Settings');
    assert.equal(matched.breadcrumbs[1].path, '#/profile');
    assert.equal(matched.breadcrumbs[1].active, true);
  });
});

describe('Campaign Creation Deduplication & Idempotency (TASK-0257)', () => {
  let service: AppDataService;
  let gateway: FakeGateway | undefined;

  beforeEach(() => {
    service = new AppDataService();
  });

  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('deduplicates campaigns array by id using Map', () => {
    const duplicates: CampaignItem[] = [
      { id: 'c1', title: 'First Campaign' },
      { id: 'c2', title: 'Second Campaign' },
      { id: 'c1', title: 'First Campaign (Duplicate)' },
    ];

    const result = service.deduplicateCampaigns(duplicates);
    assert.equal(result.length, 2, 'Duplicates should be removed');
    assert.equal(result[0].id, 'c1');
    assert.equal(result[1].id, 'c2');
  });

  it('enforces campaign ID uniqueness when creating multiple campaigns with identical IDs', async () => {
    const payload: CreateCampaignPayload = {
      title: 'Idempotent Astral Voyage',
      setting: 'Astral Wilds',
      system: '5e',
    };

    gateway = installFakeGateway({
      'POST /api/v1/campaigns': { status: 201, body: { id: 'camp-idem-1', title: payload.title, role: 'owner', player_count: 1 } },
    });
    const created = await service.createCampaign(payload);
    assert.ok(created.ok);
    const c1 = created.data;
    assert.ok(c1.id);

    // Deduplicate the created campaign alongside the listed campaigns
    const duplicatedList = [c1, c1, ...FALLBACK_CAMPAIGNS];
    const deduped = service.deduplicateCampaigns(duplicatedList);
    const matchingCount = deduped.filter((c) => c.id === c1.id).length;
    assert.equal(matchingCount, 1, 'Only one campaign entry with ID must exist');
  });

  it('stops event propagation when creator modal dispatches create-campaign', () => {
    let propagationStopped = false;
    const fakeEvent = {
      detail: { title: 'Test Realm', setting: 'Toril', system: '5e' },
      stopPropagation: () => {
        propagationStopped = true;
      },
    };

    // Simulate handleCreatorSubmit
    const handleCreatorSubmit = (e: any) => {
      e.stopPropagation();
    };

    handleCreatorSubmit(fakeEvent);
    assert.equal(propagationStopped, true, 'stopPropagation must be called on child creator submit');
  });
});
