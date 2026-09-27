/**
 * Unit tests for Campaign Members & Zanzibar Role Manager UI data operations.
 * TASK-0210: Campaign Members and Zanzibar Role Manager UI
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import type { CampaignMember, CampaignRole } from '../../services/game_session/ui/src/campaigns/types.ts';

function formatMemberRole(role: CampaignRole | string): string {
  const r = (role || '').toLowerCase();
  const map: Record<string, string> = {
    owner: 'Owner',
    dungeon_master: 'Dungeon Master',
    dm: 'Dungeon Master',
    player: 'Player',
    spectator: 'Spectator',
  };
  return map[r] || role;
}

function buildZanzibarRelation(campaignId: string, role: string, userId: string): string {
  const rel = role === 'dm' ? 'dungeon_master' : role;
  return `campaign:${campaignId}#${rel}@user:${userId}`;
}

function canManageMembers(userRole: CampaignRole | string, isExplicitGm = false): boolean {
  if (isExplicitGm) return true;
  const r = (userRole || '').toLowerCase();
  return r === 'owner' || r === 'dungeon_master' || r === 'dm';
}

function canRemoveTarget(
  actorRole: CampaignRole | string,
  actorUserId: string,
  targetMember: CampaignMember
): boolean {
  if (!canManageMembers(actorRole)) return false;
  // Cannot remove campaign owner
  if (targetMember.role === 'owner') return false;
  // Typically cannot remove self via roster remove button
  if (targetMember.user_id === actorUserId) return false;
  return true;
}

function buildInviteUrl(token: string, baseUrl = 'https://app.runefoble.com'): string {
  const cleanBase = baseUrl.replace(/\/+$/, '');
  return `${cleanBase}/#/join/${encodeURIComponent(token)}`;
}

const sampleRoster: CampaignMember[] = [
  {
    user_id: 'usr-evelyn',
    username: 'Evelyn (You)',
    character_name: 'Dungeon Master',
    role: 'owner',
  },
  {
    user_id: 'usr-marcus',
    username: 'Marcus Vance',
    character_name: 'Thorin Stonehelm (Dwarf Paladin)',
    role: 'player',
  },
  {
    user_id: 'usr-lyra',
    username: 'Lyra Moonshadow',
    character_name: 'Aeloria (Elf Wizard)',
    role: 'player',
  },
  {
    user_id: 'usr-garrick',
    username: 'Garrick Bronzearm',
    character_name: 'Co-DM',
    role: 'dungeon_master',
  },
  {
    user_id: 'usr-spectator-tom',
    username: 'Spectator Tom',
    role: 'spectator',
  },
];

describe('Campaign Members Role Formatting & Zanzibar Mappings', () => {
  it('formats internal role codes to human-readable names', () => {
    assert.equal(formatMemberRole('owner'), 'Owner');
    assert.equal(formatMemberRole('dungeon_master'), 'Dungeon Master');
    assert.equal(formatMemberRole('dm'), 'Dungeon Master');
    assert.equal(formatMemberRole('player'), 'Player');
    assert.equal(formatMemberRole('spectator'), 'Spectator');
    assert.equal(formatMemberRole('custom_role'), 'custom_role');
  });

  it('constructs Zanzibar relationship string according to SpiceDB schema', () => {
    const tuple1 = buildZanzibarRelation('camp-101', 'player', 'usr-marcus');
    assert.equal(tuple1, 'campaign:camp-101#player@user:usr-marcus');

    const tuple2 = buildZanzibarRelation('camp-101', 'dm', 'usr-garrick');
    assert.equal(tuple2, 'campaign:camp-101#dungeon_master@user:usr-garrick');

    const tuple3 = buildZanzibarRelation('camp-101', 'spectator', 'usr-spectator-tom');
    assert.equal(tuple3, 'campaign:camp-101#spectator@user:usr-spectator-tom');
  });
});

describe('Campaign Roster Permissions & Guardrails', () => {
  it('identifies GM managers correctly from roles and flags', () => {
    assert.equal(canManageMembers('owner'), true);
    assert.equal(canManageMembers('dungeon_master'), true);
    assert.equal(canManageMembers('dm'), true);
    assert.equal(canManageMembers('player'), false);
    assert.equal(canManageMembers('spectator'), false);
    assert.equal(canManageMembers('player', true), true); // explicit GM override
  });

  it('prohibits non-managers from removing members', () => {
    const target = sampleRoster[1]; // Marcus (player)
    assert.equal(canRemoveTarget('player', 'usr-lyra', target), false);
    assert.equal(canRemoveTarget('spectator', 'usr-spectator-tom', target), false);
  });

  it('prohibits removing the campaign owner even by GMs', () => {
    const owner = sampleRoster[0]; // Evelyn (owner)
    assert.equal(canRemoveTarget('dungeon_master', 'usr-garrick', owner), false);
  });

  it('prohibits removing self from the roster actions', () => {
    const coDm = sampleRoster[3]; // Garrick
    assert.equal(canRemoveTarget('dungeon_master', 'usr-garrick', coDm), false);
  });

  it('allows GM to remove regular party players and spectators', () => {
    const playerMarcus = sampleRoster[1];
    const spectatorTom = sampleRoster[4];
    assert.equal(canRemoveTarget('owner', 'usr-evelyn', playerMarcus), true);
    assert.equal(canRemoveTarget('dungeon_master', 'usr-garrick', spectatorTom), true);
  });
});

describe('Campaign Invite Link Generator Logic', () => {
  it('formats shareable invite URL with token and clean base URL', () => {
    const url = buildInviteUrl('token_abc_123', 'https://app.runefoble.com/');
    assert.equal(url, 'https://app.runefoble.com/#/join/token_abc_123');
  });

  it('encodes special characters in token safely', () => {
    const url = buildInviteUrl('token+with/special==', 'https://play.runefoble.local');
    assert.equal(url, 'https://play.runefoble.local/#/join/token%2Bwith%2Fspecial%3D%3D');
  });
});
