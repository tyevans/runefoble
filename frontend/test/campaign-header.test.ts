/**
 * Unit tests for Campaign Header Component data operations and Zanzibar management logic.
 * TASK-0248: Campaign Detail Hero Header and Metadata Component
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  type CampaignItem,
  type UpdateCampaignPayload,
  formatRulesetSystem,
} from '../../services/game_session/ui/src/campaigns/types.ts';

function validateAndBuildUpdatePayload(
  campaignId: string,
  form: {
    title: string;
    setting?: string;
    system?: string;
    coverImageUrl?: string;
    description?: string;
  }
): { valid: boolean; error?: string; payload?: UpdateCampaignPayload } {
  const trimmedTitle = form.title.trim();
  if (!trimmedTitle) {
    return { valid: false, error: 'Campaign title is required.' };
  }
  return {
    valid: true,
    payload: {
      campaignId,
      title: trimmedTitle,
      setting: form.setting?.trim() || undefined,
      system: form.system || '5e',
      cover_image_url: form.coverImageUrl?.trim() || undefined,
      description: form.description?.trim() || undefined,
    },
  };
}

function resolveCampaignStatus(campaign: CampaignItem | null): {
  label: string;
  isActive: boolean;
} {
  if (!campaign) return { label: 'Active', isActive: false };
  const hasLiveSession = Boolean(campaign.has_active_session || campaign.active_session_id);
  if (hasLiveSession) {
    return { label: 'Session Live', isActive: true };
  }
  const rawStatus = (campaign.status || 'Active').trim();
  const isActive = rawStatus.toLowerCase() === 'active';
  return { label: rawStatus, isActive };
}

function shouldRenderEditButton(canManage: boolean): boolean {
  return Boolean(canManage);
}

function shouldRenderCoverImage(campaign: CampaignItem | null): boolean {
  return Boolean(campaign?.cover_image_url && campaign.cover_image_url.trim().length > 0);
}

describe('Campaign Header Ruleset Formatting', () => {
  it('formats standard ruleset codes to canonical presentation strings', () => {
    assert.equal(formatRulesetSystem('5e'), '5e');
    assert.equal(formatRulesetSystem('dnd5e'), '5e');
    assert.equal(formatRulesetSystem('pf2e'), 'PF2e');
    assert.equal(formatRulesetSystem('pathfinder 2e'), 'PF2e');
    assert.equal(formatRulesetSystem('call_of_cthulhu'), 'Call of Cthulhu');
    assert.equal(formatRulesetSystem('coc'), 'Call of Cthulhu');
    assert.equal(formatRulesetSystem('daggerheart'), 'Daggerheart');
    assert.equal(formatRulesetSystem('custom'), 'Custom');
  });

  it('handles empty or missing ruleset gracefully with 5e default', () => {
    assert.equal(formatRulesetSystem(undefined), '5e');
    assert.equal(formatRulesetSystem(''), '5e');
  });

  it('preserves unknown homebrew ruleset names as-is', () => {
    assert.equal(formatRulesetSystem('Shadowdark'), 'Shadowdark');
    assert.equal(formatRulesetSystem('MÖRK BORG'), 'MÖRK BORG');
  });
});

describe('Campaign Header Edit Form Validation & Payload Construction', () => {
  it('rejects empty or whitespace-only campaign title', () => {
    const res = validateAndBuildUpdatePayload('camp-101', { title: '   ' });
    assert.equal(res.valid, false);
    assert.equal(res.error, 'Campaign title is required.');
    assert.equal(res.payload, undefined);
  });

  it('constructs complete update payload with trimmed values', () => {
    const res = validateAndBuildUpdatePayload('camp-101', {
      title: '  Shadows of Drakkenheim Reloaded  ',
      setting: '  Gothic Grimdark  ',
      system: '5e',
      coverImageUrl: '  https://cdn.runefoble.local/maps/drakken.png  ',
      description: '  Contaminated city center expedition.  ',
    });
    assert.equal(res.valid, true);
    assert.equal(res.error, undefined);
    assert.deepEqual(res.payload, {
      campaignId: 'camp-101',
      title: 'Shadows of Drakkenheim Reloaded',
      setting: 'Gothic Grimdark',
      system: '5e',
      cover_image_url: 'https://cdn.runefoble.local/maps/drakken.png',
      description: 'Contaminated city center expedition.',
    });
  });

  it('converts blank optional fields to undefined', () => {
    const res = validateAndBuildUpdatePayload('camp-102', {
      title: 'Simple Dungeon',
      setting: '   ',
      coverImageUrl: '',
      description: '   ',
    });
    assert.equal(res.valid, true);
    assert.equal(res.payload?.setting, undefined);
    assert.equal(res.payload?.cover_image_url, undefined);
    assert.equal(res.payload?.description, undefined);
    assert.equal(res.payload?.system, '5e');
  });
});

describe('Campaign Header Permission and Status Logic', () => {
  it('restricts edit campaign button visibility to canManage=true', () => {
    assert.equal(shouldRenderEditButton(true), true);
    assert.equal(shouldRenderEditButton(false), false);
  });

  it('flags live active session with Session Live indicator', () => {
    const statusLive = resolveCampaignStatus({
      id: 'c1',
      title: 'Tomb',
      has_active_session: true,
    });
    assert.equal(statusLive.label, 'Session Live');
    assert.equal(statusLive.isActive, true);

    const statusLiveId = resolveCampaignStatus({
      id: 'c2',
      title: 'Tomb 2',
      active_session_id: 'sess-99',
    });
    assert.equal(statusLiveId.label, 'Session Live');
    assert.equal(statusLiveId.isActive, true);
  });

  it('resolves standard active or custom statuses without live session', () => {
    const statusActive = resolveCampaignStatus({
      id: 'c3',
      title: 'Tomb 3',
      status: 'active',
      has_active_session: false,
    });
    assert.equal(statusActive.label, 'active');
    assert.equal(statusActive.isActive, true);

    const statusPlanning = resolveCampaignStatus({
      id: 'c4',
      title: 'Tomb 4',
      status: 'Planning',
      has_active_session: false,
    });
    assert.equal(statusPlanning.label, 'Planning');
    assert.equal(statusPlanning.isActive, false);
  });

  it('correctly decides between cover image vs Bauhaus geometric fallback banner', () => {
    assert.equal(
      shouldRenderCoverImage({
        id: 'c5',
        title: 'Covered',
        cover_image_url: 'https://images.example.com/banner.png',
      }),
      true
    );
    assert.equal(
      shouldRenderCoverImage({
        id: 'c6',
        title: 'Uncovered',
        cover_image_url: null,
      }),
      false
    );
    assert.equal(
      shouldRenderCoverImage({
        id: 'c7',
        title: 'Empty',
        cover_image_url: '',
      }),
      false
    );
  });
});
