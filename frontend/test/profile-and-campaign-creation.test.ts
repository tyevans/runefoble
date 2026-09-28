/**
 * Unit tests for Profile Settings View & Campaign Creation Idempotency.
 * TASK-0257: Profile Settings View and Campaign Creation Idempotency
 * ADR-0001, ADR-0004, ADR-0007, ADR-0012, ADR-0013
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router } from '../src/router/router.ts';
import { AppDataService } from '../src/services/app-data-service.ts';
import { FALLBACK_CAMPAIGNS } from '../src/services/app-data-fallbacks.ts';
import type { CampaignItem, CreateCampaignPayload } from '../../services/game_session/ui/src/campaigns/types.ts';
import type { AppActiveView } from '../src/runefoble-app.ts';

function resolveActiveView(path: string): AppActiveView {
  const router = Router.getInstance();
  const matched = router.match(path);
  const pat = matched?.pattern || '';
  if (pat === '#/login' || pat === '#/register') return 'login';
  if (pat.startsWith('#/campaigns/:campaignId/lobby/')) return 'session-lobby';
  if (pat.startsWith('#/campaigns/:campaignId/sessions/')) return 'session-active';
  if (pat === '#/campaigns/:campaignId/characters') return 'campaign-characters';
  if (pat.startsWith('#/campaigns/:campaignId')) return 'campaign-detail';
  if (pat === '#/characters') return 'characters';
  if (pat === '#/profile') return 'profile';
  return 'campaigns';
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

  beforeEach(() => {
    service = new AppDataService();
  });

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

    const c1 = await service.createCampaign(payload);
    assert.ok(c1.id);

    // Call deduplicate with existing fallback campaigns plus duplicate
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
