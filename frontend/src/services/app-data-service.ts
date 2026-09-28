import type { CampaignItem, CampaignMember, CreateCampaignPayload, UpdateCampaignPayload } from '@runefoble/game-session-ui';
import type { LobbyParticipant, LobbyCharacterOption } from '@runefoble/game-session-ui';
import type { CharacterItem, RosterCampaignOption, CreateCharacterPayload } from '@runefoble/character-sheet-ui';
import type { BoardToken } from '@runefoble/board-state-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';
import type { CampaignSessionItem } from '../components/runefoble-session-list.ts';
import { authService, type UserClaims } from '../auth/auth-service.ts';
import {
  FALLBACK_CAMPAIGNS,
  FALLBACK_CHARACTERS,
  buildFallbackCharacterDetail,
} from './fallback-data.ts';
export { FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS };

export class AppDataService {
  private static instance: AppDataService;
  public apiBase = '/api/v1';

  static getInstance(): AppDataService {
    if (!AppDataService.instance) AppDataService.instance = new AppDataService();
    return AppDataService.instance;
  }

  private getAuthHeaders(): HeadersInit {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    const token = authService.getAccessToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const user = authService.getUser();
    if (user?.user_id) headers['X-User-Id'] = user.user_id;
    return headers;
  }

  public deduplicateCampaigns(campaigns: CampaignItem[]): CampaignItem[] {
    const map = new Map<string, CampaignItem>();
    for (const c of campaigns) if (!map.has(c.id)) map.set(c.id, c);
    return Array.from(map.values());
  }

  async fetchCampaigns(): Promise<CampaignItem[]> {
    try {
      const res = await fetch(`${this.apiBase}/campaigns`, { headers: this.getAuthHeaders() });
      if (res.ok) return this.deduplicateCampaigns(await res.json());
    } catch { /* fallback */ }
    const deduped = this.deduplicateCampaigns(FALLBACK_CAMPAIGNS);
    FALLBACK_CAMPAIGNS.length = 0;
    FALLBACK_CAMPAIGNS.push(...deduped);
    return [...FALLBACK_CAMPAIGNS];
  }

  async fetchProfile(): Promise<UserClaims | null> {
    try {
      const res = await fetch(`${this.apiBase}/profile`, { headers: this.getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    return authService.getUser() || { user_id: 'user-valeros', username: 'Valeros', email: 'valeros@runefoble.local', roles: ['player'], is_admin: false };
  }

  async fetchCampaign(campaignId: string): Promise<CampaignItem | null> {
    try {
      const res = await fetch(`${this.apiBase}/campaigns/${campaignId}`, { headers: this.getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    return FALLBACK_CAMPAIGNS.find((c) => c.id === campaignId) || {
      id: campaignId,
      title: `Campaign #${campaignId}`,
      role: 'player',
      player_count: 3,
      has_active_session: false,
    };
  }

  async fetchCampaignMembers(campaignId: string): Promise<CampaignMember[]> {
    try {
      const res = await fetch(`${this.apiBase}/campaigns/${campaignId}/members`, { headers: this.getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    return [
      { user_id: 'user-valeros', username: 'Valeros (You)', character_name: 'Valeros of Korvosa', role: 'owner' },
      { user_id: 'user-kyra', username: 'Kyra Sunfall', character_name: 'Kyra the Sun Maiden', role: 'player' },
      { user_id: 'user-merisiel', username: 'Merisiel Nightshadow', character_name: 'Merisiel', role: 'player' },
    ];
  }

  async fetchCampaignSessions(campaignId: string): Promise<CampaignSessionItem[]> {
    try {
      const res = await fetch(`${this.apiBase}/campaigns/${campaignId}/sessions`, { headers: this.getAuthHeaders() });
      if (res.ok) {
        const items = await res.json();
        return items.map((item: any) => ({
          ...item,
          campaignId: item.campaign_id || item.campaignId,
          participantsCount: item.participants_count ?? item.participantsCount ?? 0,
        }));
      }
    } catch { /* fallback */ }
    return [
      {
        id: campaignId === '4' ? 'session-tomb-14' : `session-${campaignId}-1`,
        campaignId,
        title: campaignId === '4' ? 'Session #14: Tomb of the Star-Eater' : `Session #1 (${campaignId})`,
        status: 'active',
        round: 3,
        participantsCount: 4,
      },
      {
        id: `lobby-${campaignId}-2`,
        campaignId,
        title: 'Session #15: Chamber of Horrors',
        status: 'lobby',
        participantsCount: 3,
      },
    ];
  }

  async fetchSession(sessionId: string): Promise<CampaignSessionItem | null> {
    try {
      const res = await fetch(`${this.apiBase}/sessions/${sessionId}`, { headers: this.getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        return {
          id: data.id || sessionId,
          campaignId: data.campaign_id || data.campaignId || '',
          title: data.title || (sessionId === '14' || sessionId === 'session-tomb-14' ? 'Session #14' : `Session #${sessionId}`),
          status: data.status || 'active',
          round: data.round || 1,
          participantsCount: Array.isArray(data.participants) ? data.participants.length : (data.participantsCount || 0),
        };
      }
    } catch { /* fallback */ }
    if (sessionId === '14' || sessionId === 'session-tomb-14') {
      return {
        id: sessionId,
        campaignId: '4',
        title: 'Session #14: Tomb of the Star-Eater',
        status: 'active',
        round: 3,
        participantsCount: 4,
      };
    }
    if (sessionId === '15' || sessionId.startsWith('lobby-')) {
      return {
        id: sessionId,
        campaignId: '4',
        title: sessionId === '15' ? 'Lobby 15' : 'Session #15: Chamber of Horrors',
        status: 'lobby',
        participantsCount: 3,
      };
    }
    return {
      id: sessionId,
      campaignId: '',
      title: `Session #${sessionId}`,
      status: 'active',
      round: 1,
      participantsCount: 3,
    };
  }

  async fetchCharacters(): Promise<CharacterItem[]> {
    try {
      const res = await fetch(`${this.apiBase}/characters`, { headers: this.getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    return [...FALLBACK_CHARACTERS];
  }

  getFallbackCharacterName(id: string): string | undefined {
    return FALLBACK_CHARACTERS.find((c) => c.id === id)?.name;
  }

  async fetchCharacter(characterId: string): Promise<any | null> {
    try {
      const res = await fetch(`${this.apiBase}/characters/${characterId}`, { headers: this.getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    const char = FALLBACK_CHARACTERS.find((c) => c.id === characterId);
    return buildFallbackCharacterDetail(char, characterId);
  }

  async fetchRosterCampaignOptions(): Promise<RosterCampaignOption[]> {
    const campaigns = await this.fetchCampaigns();
    return campaigns.map((c) => ({ id: c.id, title: c.title }));
  }

  async createCharacter(payload: CreateCharacterPayload): Promise<CharacterItem> {
    try {
      const res = await fetch(`${this.apiBase}/characters`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    const newChar: CharacterItem = {
      id: `char-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      name: payload.name,
      characterClass: payload.characterClass,
      subclass: payload.subclass,
      level: payload.level || 1,
      currentHp: payload.maxHp,
      maxHp: payload.maxHp,
      armorClass: payload.armorClass,
      speed: payload.speed || 30,
      portraitUrl: payload.portraitUrl,
      campaignId: null,
      campaignTitle: null,
      ownerId: authService.getUser()?.user_id || 'user-valeros',
    };
    FALLBACK_CHARACTERS.unshift(newChar);
    return newChar;
  }

  async assignCharacterCampaign(characterId: string, campaignId: string | null): Promise<void> {
    try {
      const res = await fetch(`${this.apiBase}/characters/${characterId}/campaign`, {
        method: 'PATCH',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ campaignId }),
      });
      if (res.ok) return;
    } catch { /* fallback */ }
    const char = FALLBACK_CHARACTERS.find((c) => c.id === characterId);
    if (char) {
      char.campaignId = campaignId;
      const camp = FALLBACK_CAMPAIGNS.find((c) => c.id === campaignId);
      char.campaignTitle = camp ? camp.title : null;
    }
  }

  async deleteCharacter(characterId: string): Promise<void> {
    try {
      const res = await fetch(`${this.apiBase}/characters/${characterId}`, {
        method: 'DELETE',
        headers: this.getAuthHeaders(),
      });
      if (res.ok) return;
    } catch { /* fallback */ }
    const idx = FALLBACK_CHARACTERS.findIndex((c) => c.id === characterId);
    if (idx !== -1) {
      FALLBACK_CHARACTERS.splice(idx, 1);
    }
  }

  async fetchLobbyState(
    arg1: string,
    arg2?: string
  ): Promise<{
    participants: LobbyParticipant[];
    availableCharacters: LobbyCharacterOption[];
  }> {
    const isArg1Session = arg1.startsWith('session-') || arg1.startsWith('lobby-');
    const sessionId = arg2 !== undefined ? (isArg1Session ? arg1 : arg2) : arg1;
    const campaignId = arg2 !== undefined ? (isArg1Session ? arg2 : arg1) : undefined;
    let participants: LobbyParticipant[] = [];
    try {
      const res = await fetch(`${this.apiBase}/sessions/${sessionId}`, { headers: this.getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (data.participants) participants = data.participants;
      }
    } catch { /* fallback */ }

    if (participants.length === 0) {
      participants = [
        { userId: 'user-valeros', username: 'Valeros', role: 'Fighter Lvl 4', characterId: 'char-valeros', characterName: 'Valeros of Korvosa', characterClass: 'Fighter', characterLevel: 4, isReady: true, isAbsent: false, onlineStatus: 'online' },
        { userId: 'user-kyra', username: 'Kyra', role: 'Cleric Lvl 4', characterId: 'char-kyra', characterName: 'Kyra the Sun Maiden', characterClass: 'Cleric', characterLevel: 4, isReady: false, isAbsent: true, onlineStatus: 'offline' },
      ];
    }

    const characters = await this.fetchCharacters();
    const sorted = campaignId
      ? [
          ...characters.filter((c) => c.campaignId === campaignId),
          ...characters.filter((c) => !c.campaignId),
          ...characters.filter((c) => c.campaignId && c.campaignId !== campaignId),
        ]
      : characters;

    const availableCharacters: LobbyCharacterOption[] = sorted.map((c) => ({
      id: c.id,
      name: c.name,
      characterClass: c.characterClass,
      level: c.level,
      portraitUrl: c.portraitUrl,
    }));

    return { participants, availableCharacters };
  }

  async fetchBoardTokens(sessionId: string): Promise<BoardToken[]> {
    try {
      const res = await fetch(`${this.apiBase}/boards/${sessionId}`, { headers: this.getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (data.tokens) return data.tokens;
      }
    } catch { /* fallback */ }
    return [
      { id: '1', name: 'Valeros', x: 2, y: 3, color: 'var(--rf-accent-secondary)', hp: 38, maxHp: 45, visionRadius: 2 },
      { id: '2', name: 'Kyra (AI)', x: 3, y: 3, isAiControlled: true, color: 'var(--rf-accent-primary)', hp: 28, maxHp: 32, visionRadius: 2 },
      { id: '3', name: 'Goblin Scout', x: 5, y: 1, isHostile: true, color: 'var(--rf-accent-tertiary)', hp: 7, maxHp: 12 },
      { id: '4', name: 'Red Dragon Wyrmling', x: 6, y: 5, isHostile: true, color: 'var(--rf-border-color)', hp: 52, maxHp: 75 },
    ];
  }

  async fetchSessionEvents(_sessionId: string): Promise<WatcherFeedEvent[]> {
    return [
      { id: '1', timestamp: '19:45:00', source: 'watcher_dm', speaker: 'The Watcher (AI DM)', text: 'Welcome back, adventurers.', actionType: 'dm_ruling' },
      { id: '2', timestamp: '19:45:20', source: 'player', speaker: 'Valeros', text: '"I ready my shield and move two steps forward."', actionType: 'speech' },
      { id: '3', timestamp: '19:45:30', source: 'stand_in', speaker: 'Kyra (AI Stand-in, Drunk)', text: '"Hah! No dragon can outwit Sarenrae finest vintner!"', actionType: 'speech' },
    ];
  }

  async createCampaignSession(
    campaignId: string,
    payload: { title: string; status?: string; scheduled_at?: string; description?: string }
  ): Promise<CampaignSessionItem> {
    try {
      const res = await fetch(`${this.apiBase}/campaigns/${campaignId}/sessions`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const item = await res.json();
        return {
          ...item,
          campaignId: item.campaign_id || item.campaignId,
          participantsCount: item.participants_count ?? item.participantsCount ?? 0,
        };
      }
    } catch { /* fallback */ }
    const fallbackId = `lobby-${campaignId}-${Date.now()}`;
    return {
      id: fallbackId,
      campaignId,
      title: payload.title,
      status: (payload.status as any) || 'lobby',
      participantsCount: 1,
    };
  }

  async createCampaign(payload: CreateCampaignPayload): Promise<CampaignItem> {
    let created: CampaignItem | null = null;
    try {
      const res = await fetch(`${this.apiBase}/campaigns`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (res.ok) created = await res.json();
    } catch { /* fallback */ }
    if (!created) {
      created = {
        id: `camp-${Date.now()}`,
        title: payload.title,
        description: payload.description,
        setting: payload.setting,
        system: payload.system || '5e',
        role: 'owner',
        player_count: 1,
        has_active_session: false,
      };
    }
    const deduped = this.deduplicateCampaigns([created, ...FALLBACK_CAMPAIGNS]);
    FALLBACK_CAMPAIGNS.length = 0;
    FALLBACK_CAMPAIGNS.push(...deduped);
    return created;
  }

  async updateCampaign(campaignId: string, payload: UpdateCampaignPayload): Promise<CampaignItem | null> {
    try {
      const res = await fetch(`${this.apiBase}/campaigns/${campaignId}`, {
        method: 'PATCH',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    const c = FALLBACK_CAMPAIGNS.find((item) => item.id === campaignId);
    if (c) {
      if (payload.title !== undefined) c.title = payload.title;
      if (payload.setting !== undefined) c.setting = payload.setting;
      if (payload.system !== undefined) c.system = payload.system;
      if (payload.cover_image_url !== undefined) c.cover_image_url = payload.cover_image_url;
      if (payload.description !== undefined) c.description = payload.description;
      return { ...c };
    }
    return {
      id: campaignId,
      title: payload.title,
      setting: payload.setting,
      system: payload.system || '5e',
      cover_image_url: payload.cover_image_url,
      description: payload.description,
    };
  }
}

export const appDataService = AppDataService.getInstance();
