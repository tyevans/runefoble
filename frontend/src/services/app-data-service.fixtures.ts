import type {
  CampaignItem, CampaignMember, LobbyParticipant, CreateCampaignPayload, UpdateCampaignPayload, LobbyCharacterOption,
} from '@runefoble/game-session-ui';
import type { CharacterItem, CreateCharacterPayload } from '@runefoble/character-sheet-ui';
import type { BoardToken } from '@runefoble/board-state-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';
import type { CampaignSessionItem } from '../components/runefoble-session-list.ts';
import type { UserClaims } from '../auth/auth-service.ts';

export interface InviteResponse {
  token: string; campaign_id: string; role: string; invite_url: string; expires_at?: string | null; created_at: string; max_uses?: number | null; uses?: number;
}

export const FALLBACK_PROFILE: UserClaims = {
  user_id: 'user-valeros', username: 'Valeros', email: 'valeros@runefoble.local', roles: ['player'], is_admin: false,
};

export const FALLBACK_CAMPAIGNS: CampaignItem[] = [
  { id: '4', title: 'Tomb of the Star-Eater', system: '5e', role: 'owner', owner_id: 'user-valeros', description: 'Ancient celestial horrors slumber beneath the irradiated astral sands.', setting: 'Spelljammer Astral Void', dm_name: 'The Watcher', player_count: 4, has_active_session: true, active_session_id: 'session-tomb-14' },
  { id: '5', title: 'Whispering Depths', system: '5e', role: 'player', owner_id: 'user-evelyn', description: 'Subterranean aquatic expeditions through forgotten dwarven aqueducts.', setting: 'Underdark Aquatics', dm_name: 'Evelyn Vance', player_count: 5, has_active_session: false },
];

export const FALLBACK_CHARACTERS: CharacterItem[] = [
  { id: 'char-valeros', name: 'Valeros of Korvosa', characterClass: 'Fighter', subclass: 'Battle Master', level: 4, currentHp: 38, maxHp: 45, armorClass: 18, speed: 30, campaignId: '4', campaignTitle: 'Tomb of the Star-Eater', portraitUrl: '/assets/portraits/fighter.svg' },
  { id: 'char-kyra', name: 'Kyra the Sun Maiden', characterClass: 'Cleric', subclass: 'Life Domain', level: 4, currentHp: 28, maxHp: 32, armorClass: 16, speed: 25, campaignId: '4', campaignTitle: 'Tomb of the Star-Eater', portraitUrl: '/assets/portraits/cleric.svg' },
  { id: 'char-ezren', name: 'Ezren the Gray', characterClass: 'Wizard', subclass: 'Evocation', level: 5, currentHp: 22, maxHp: 26, armorClass: 12, speed: 30, campaignId: null, campaignTitle: null, portraitUrl: '/assets/portraits/wizard.svg' },
];

export const FALLBACK_MEMBERS: CampaignMember[] = [
  { user_id: 'user-valeros', username: 'Valeros (You)', character_name: 'Valeros of Korvosa', role: 'owner' },
  { user_id: 'user-kyra', username: 'Kyra Sunfall', character_name: 'Kyra the Sun Maiden', role: 'player' },
  { user_id: 'user-merisiel', username: 'Merisiel Nightshadow', character_name: 'Merisiel', role: 'player' },
];

const CAMPAIGN_MEMBERS_CACHE: Record<string, CampaignMember[]> = {
  '4': [
    { user_id: 'user-valeros', username: 'Valeros (You)', character_name: 'Valeros of Korvosa', role: 'owner' },
    { user_id: 'user-kyra', username: 'Kyra Sunfall', character_name: 'Kyra the Sun Maiden', role: 'player' },
    { user_id: 'user-merisiel', username: 'Merisiel Nightshadow', character_name: 'Merisiel', role: 'player' },
  ],
};

export function getFallbackCampaignMembers(campaignId: string): CampaignMember[] {
  if (!CAMPAIGN_MEMBERS_CACHE[campaignId]) {
    const c = FALLBACK_CAMPAIGNS.find((item) => item.id === campaignId);
    const owner = c?.owner_id || 'user-valeros';
    const name = owner === 'user-valeros' ? 'Valeros (You)' : (c?.dm_name || owner);
    CAMPAIGN_MEMBERS_CACHE[campaignId] = [{ user_id: owner, username: name, role: 'owner' }];
  }
  return CAMPAIGN_MEMBERS_CACHE[campaignId];
}

export function assignFallbackMemberRole(campaignId: string, userId: string, role: string): void {
  const m = getFallbackCampaignMembers(campaignId).find((x) => x.user_id === userId);
  if (m) m.role = role as any;
}

export function removeFallbackMember(campaignId: string, userId: string): void {
  const list = getFallbackCampaignMembers(campaignId);
  const idx = list.findIndex((x) => x.user_id === userId);
  if (idx !== -1) list.splice(idx, 1);
}

export function createFallbackInvite(campaignId: string, role: string, expiresInHours = 72, maxUses?: number): InviteResponse {
  const token = `inv-${Math.random().toString(36).substring(2, 10)}`;
  const origin = typeof window !== 'undefined' && window.location?.origin ? window.location.origin : 'https://runefoble.local';
  return {
    token, campaign_id: campaignId, role, invite_url: `${origin}/#/join/${token}`,
    created_at: new Date().toISOString(), expires_at: new Date(Date.now() + expiresInHours * 3600000).toISOString(),
    max_uses: maxUses ?? null, uses: 0,
  };
}

export const FALLBACK_PARTICIPANTS: LobbyParticipant[] = [
  { userId: 'user-valeros', username: 'Valeros', role: 'Fighter Lvl 4', characterId: 'char-valeros', characterName: 'Valeros of Korvosa', characterClass: 'Fighter', characterLevel: 4, isReady: true, isAbsent: false, onlineStatus: 'online' },
  { userId: 'user-kyra', username: 'Kyra', role: 'Cleric Lvl 4', characterId: 'char-kyra', characterName: 'Kyra the Sun Maiden', characterClass: 'Cleric', characterLevel: 4, isReady: false, isAbsent: true, onlineStatus: 'offline' },
];

export const FALLBACK_SESSIONS: CampaignSessionItem[] = [
  { id: 'session-tomb-14', campaignId: '4', title: 'Session #14: Tomb of the Star-Eater', status: 'active', round: 3, participantsCount: 4 },
  { id: 'lobby-4-2', campaignId: '4', title: 'Session #15: Chamber of Horrors', status: 'lobby', participantsCount: 3 },
];

export function getFallbackCampaignSessions(campaignId: string): CampaignSessionItem[] {
  return [
    { id: campaignId === '4' ? 'session-tomb-14' : `session-${campaignId}-1`, campaignId, title: campaignId === '4' ? 'Session #14: Tomb of the Star-Eater' : `Session #1 (${campaignId})`, status: 'active', round: 3, participantsCount: 4 },
    { id: `lobby-${campaignId}-2`, campaignId, title: 'Session #15: Chamber of Horrors', status: 'lobby', participantsCount: 3 },
  ];
}

export function getFallbackSession(sessionId: string): CampaignSessionItem {
  if (sessionId === '14' || sessionId === 'session-tomb-14') return { id: sessionId, campaignId: '4', title: 'Session #14: Tomb of the Star-Eater', status: 'active', round: 3, participantsCount: 4 };
  if (sessionId === '15' || sessionId.startsWith('lobby-')) return { id: sessionId, campaignId: '4', title: sessionId === '15' ? 'Lobby 15' : 'Session #15: Chamber of Horrors', status: 'lobby', participantsCount: 3 };
  return { id: sessionId, campaignId: '', title: `Session #${sessionId}`, status: 'active', round: 1, participantsCount: 3 };
}

export function createFallbackCampaign(campaignId: string): CampaignItem {
  return { id: campaignId, title: `Campaign #${campaignId}`, role: 'player', player_count: 3, has_active_session: false };
}

export function createFallbackCampaignItem(payload: CreateCampaignPayload, ownerId = 'user-valeros'): CampaignItem {
  const id = `camp-${Date.now()}`;
  const uname = ownerId === 'user-valeros' ? 'Valeros (You)' : ownerId;
  CAMPAIGN_MEMBERS_CACHE[id] = [{ user_id: ownerId, username: uname, role: 'owner' }];
  return { id, title: payload.title, description: payload.description, owner_id: ownerId, setting: payload.setting, system: payload.system || '5e', role: 'owner', player_count: 1, has_active_session: false };
}

export function updateFallbackCampaign(campaignId: string, payload: UpdateCampaignPayload): CampaignItem {
  const c = FALLBACK_CAMPAIGNS.find((item) => item.id === campaignId);
  if (c) {
    if (payload.title !== undefined) c.title = payload.title;
    if (payload.setting !== undefined) c.setting = payload.setting;
    if (payload.system !== undefined) c.system = payload.system;
    if (payload.cover_image_url !== undefined) c.cover_image_url = payload.cover_image_url;
    if (payload.description !== undefined) c.description = payload.description;
    return { ...c };
  }
  return { id: campaignId, title: payload.title, setting: payload.setting, system: payload.system || '5e', cover_image_url: payload.cover_image_url, description: payload.description };
}

export function createFallbackCharacter(payload: CreateCharacterPayload, ownerId: string): CharacterItem {
  return { id: `char-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, name: payload.name, characterClass: payload.characterClass, subclass: payload.subclass, level: payload.level || 1, currentHp: payload.maxHp, maxHp: payload.maxHp, armorClass: payload.armorClass, speed: payload.speed || 30, portraitUrl: payload.portraitUrl, campaignId: null, campaignTitle: null, ownerId };
}

export function assignFallbackCharacterCampaign(characterId: string, campaignId: string | null): void {
  const char = FALLBACK_CHARACTERS.find((c) => c.id === characterId);
  if (char) { char.campaignId = campaignId; const camp = FALLBACK_CAMPAIGNS.find((c) => c.id === campaignId); char.campaignTitle = camp ? camp.title : null; }
}

export function deleteFallbackCharacter(characterId: string): void {
  const idx = FALLBACK_CHARACTERS.findIndex((c) => c.id === characterId);
  if (idx !== -1) FALLBACK_CHARACTERS.splice(idx, 1);
}

export function resolveLobbyAvailableCharacters(characters: CharacterItem[], campaignId?: string): LobbyCharacterOption[] {
  const sorted = campaignId ? [...characters.filter((c) => c.campaignId === campaignId), ...characters.filter((c) => !c.campaignId), ...characters.filter((c) => c.campaignId && c.campaignId !== campaignId)] : characters;
  return sorted.map((c) => ({ id: c.id, name: c.name, characterClass: c.characterClass, level: c.level, portraitUrl: c.portraitUrl }));
}

export const FALLBACK_BOARD_TOKENS: BoardToken[] = [
  { id: '1', name: 'Valeros', x: 2, y: 3, color: 'var(--rf-accent-secondary)', hp: 38, maxHp: 45, visionRadius: 2 },
  { id: '2', name: 'Kyra (AI)', x: 3, y: 3, isAiControlled: true, color: 'var(--rf-accent-primary)', hp: 28, maxHp: 32, visionRadius: 2 },
  { id: '3', name: 'Goblin Scout', x: 5, y: 1, isHostile: true, color: 'var(--rf-accent-tertiary)', hp: 7, maxHp: 12 },
  { id: '4', name: 'Red Dragon Wyrmling', x: 6, y: 5, isHostile: true, color: 'var(--rf-border-color)', hp: 52, maxHp: 75 },
];

export const FALLBACK_SESSION_EVENTS: WatcherFeedEvent[] = [
  { id: '1', timestamp: '19:45:00', source: 'watcher_dm', speaker: 'The Watcher (AI DM)', text: 'Welcome back, adventurers.', actionType: 'dm_ruling' },
  { id: '2', timestamp: '19:45:20', source: 'player', speaker: 'Valeros', text: '"I ready my shield and move two steps forward."', actionType: 'speech' },
  { id: '3', timestamp: '19:45:30', source: 'stand_in', speaker: 'Kyra (AI Stand-in, Drunk)', text: '"Hah! No dragon can outwit Sarenrae finest vintner!"', actionType: 'speech' },
];
