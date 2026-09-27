/**
 * Unit tests for Campaign Dashboard and Creator data transformations & filtering.
 * TASK-0209: Campaign Dashboard and Creation Microfrontend
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import type { CampaignItem, RoleFilter, CreateCampaignPayload } from '../../services/game_session/ui/src/campaigns/types.ts';

// Helper matching logic mirroring RunefobleCampaignDashboard
function isDMing(c: CampaignItem, userId = ''): boolean {
  const r = (c.role || '').toLowerCase();
  if (r === 'owner' || r === 'dungeon_master' || r === 'dm') return true;
  if (userId && c.owner_id === userId) return true;
  return false;
}

function filterCampaigns(
  campaigns: CampaignItem[],
  filter: RoleFilter,
  searchQuery: string,
  userId = ''
): CampaignItem[] {
  return campaigns.filter((c) => {
    if (filter === 'dming' && !isDMing(c, userId)) return false;
    if (filter === 'playing' && isDMing(c, userId)) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      const titleMatch = (c.title || '').toLowerCase().includes(q);
      const descMatch = (c.description || '').toLowerCase().includes(q);
      const settingMatch = (c.setting || '').toLowerCase().includes(q);
      const dmMatch = (c.dm_name || c.owner_id || '').toLowerCase().includes(q);
      if (!titleMatch && !descMatch && !settingMatch && !dmMatch) return false;
    }
    return true;
  });
}

function validateAndBuildCreatePayload(form: {
  title: string;
  setting?: string;
  system?: string;
  coverImageUrl?: string;
  description?: string;
}): { valid: boolean; error?: string; payload?: CreateCampaignPayload } {
  const trimmedTitle = form.title.trim();
  if (!trimmedTitle) {
    return { valid: false, error: 'Campaign title is required.' };
  }
  return {
    valid: true,
    payload: {
      title: trimmedTitle,
      setting: (form.setting || '').trim(),
      system: form.system || '5e',
      cover_image_url: form.coverImageUrl?.trim() || undefined,
      description: form.description?.trim() || undefined,
    },
  };
}

const testCampaigns: CampaignItem[] = [
  {
    id: 'camp-1',
    title: 'Shadows of Drakkenheim',
    description: 'Contaminated gothic ruins filled with eldritch horrors.',
    setting: 'Gothic Fantasy',
    system: '5e',
    role: 'owner',
    owner_id: 'user-evelyn',
    dm_name: 'Evelyn',
    player_count: 4,
    has_active_session: true,
  },
  {
    id: 'camp-2',
    title: 'Curse of Strahd',
    description: 'Vampiric dread in the mist-shrouded land of Barovia.',
    setting: 'Gothic Horror',
    system: '5e',
    role: 'player',
    owner_id: 'user-marcus',
    dm_name: 'Marcus',
    player_count: 5,
    has_active_session: false,
  },
  {
    id: 'camp-3',
    title: 'Frontier Caravan Run',
    description: 'Guarding mercantile wagons across the West Marches.',
    setting: 'High Fantasy',
    system: 'pf2e',
    role: 'dungeon_master',
    owner_id: 'user-evelyn',
    dm_name: 'Evelyn',
    player_count: 6,
    has_active_session: false,
  },
  {
    id: 'camp-4',
    title: 'Whispers of the Deep',
    description: 'Underwater cosmic mystery in sunken ruins.',
    setting: 'Lovecraftian Ocean',
    system: 'call_of_cthulhu',
    role: 'spectator',
    owner_id: 'user-sarah',
    dm_name: 'Sarah',
    player_count: 3,
    has_active_session: true,
  },
];

describe('Campaign Dashboard Filtering Logic', () => {
  it('returns all campaigns when filter is "all"', () => {
    const results = filterCampaigns(testCampaigns, 'all', '');
    assert.equal(results.length, 4);
  });

  it('filters campaigns for DMing roles (owner, dungeon_master, dm)', () => {
    const results = filterCampaigns(testCampaigns, 'dming', '');
    assert.equal(results.length, 2);
    assert.deepEqual(results.map((c) => c.id).sort(), ['camp-1', 'camp-3']);
  });

  it('filters campaigns for Playing roles (player, spectator, non-DM)', () => {
    const results = filterCampaigns(testCampaigns, 'playing', '');
    assert.equal(results.length, 2);
    assert.deepEqual(results.map((c) => c.id).sort(), ['camp-2', 'camp-4']);
  });

  it('matches campaigns by text search across title, description, and setting', () => {
    const titleMatch = filterCampaigns(testCampaigns, 'all', 'Drakkenheim');
    assert.equal(titleMatch.length, 1);
    assert.equal(titleMatch[0].id, 'camp-1');

    const descMatch = filterCampaigns(testCampaigns, 'all', 'mist-shrouded');
    assert.equal(descMatch.length, 1);
    assert.equal(descMatch[0].id, 'camp-2');

    const settingMatch = filterCampaigns(testCampaigns, 'all', 'Lovecraftian');
    assert.equal(settingMatch.length, 1);
    assert.equal(settingMatch[0].id, 'camp-4');
  });

  it('combines role filter and text search query', () => {
    // Both Drakkenheim and Strahd are Gothic, but only Drakkenheim is DMing
    const results = filterCampaigns(testCampaigns, 'dming', 'Gothic');
    assert.equal(results.length, 1);
    assert.equal(results[0].id, 'camp-1');
  });
});

describe('Campaign Creator Form Validation & Payload Building', () => {
  it('rejects empty campaign title', () => {
    const res = validateAndBuildCreatePayload({ title: '   ' });
    assert.equal(res.valid, false);
    assert.equal(res.error, 'Campaign title is required.');
    assert.equal(res.payload, undefined);
  });

  it('constructs complete creation payload with defaults', () => {
    const res = validateAndBuildCreatePayload({
      title: 'Tomb of the Star-Eater',
      setting: 'Spelljammer Sci-Fi',
      system: '5e',
      coverImageUrl: 'https://cdn.runefoble.local/maps/star.png',
      description: 'Journey to the dead stars.',
    });
    assert.equal(res.valid, true);
    assert.equal(res.error, undefined);
    assert.deepEqual(res.payload, {
      title: 'Tomb of the Star-Eater',
      setting: 'Spelljammer Sci-Fi',
      system: '5e',
      cover_image_url: 'https://cdn.runefoble.local/maps/star.png',
      description: 'Journey to the dead stars.',
    });
  });

  it('defaults ruleset system to 5e when not specified', () => {
    const res = validateAndBuildCreatePayload({
      title: 'Simple Quest',
    });
    assert.equal(res.valid, true);
    assert.equal(res.payload?.system, '5e');
  });
});
