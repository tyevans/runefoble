import type {
  CampaignItem, CampaignMember, CreateCampaignPayload, UpdateCampaignPayload,
  LobbyParticipant, LobbyCharacterOption,
} from '@runefoble/game-session-ui';
import type { CharacterItem, RosterCampaignOption, CreateCharacterPayload } from '@runefoble/character-sheet-ui';
import type { BoardToken } from '@runefoble/board-state-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';
import type { CampaignSessionItem } from '../components/runefoble-session-list.ts';
import { authService, type UserClaims } from '../auth/auth-service.ts';
import { buildFallbackCharacterDetail } from './fallback-data.ts';
import {
  FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS, FALLBACK_MEMBERS, FALLBACK_PARTICIPANTS,
  FALLBACK_SESSIONS, FALLBACK_PROFILE, FALLBACK_BOARD_TOKENS, FALLBACK_SESSION_EVENTS,
  getFallbackCampaignSessions, getFallbackSession, createFallbackCampaign,
  createFallbackCampaignItem, updateFallbackCampaign, createFallbackCharacter,
  assignFallbackCharacterCampaign, deleteFallbackCharacter, resolveLobbyAvailableCharacters,
  getFallbackCampaignMembers, assignFallbackMemberRole, removeFallbackMember,
  createFallbackInvite, type InviteResponse,
} from './app-data-service.fixtures.ts';

export { FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS, FALLBACK_MEMBERS, FALLBACK_PARTICIPANTS, FALLBACK_SESSIONS, type InviteResponse };

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

  private async request<T>(path: string, init?: RequestInit): Promise<T | null> {
    const url = path.startsWith(this.apiBase) ? path : `${this.apiBase}${path}`;
    try {
      const res = await fetch(url, { headers: this.getAuthHeaders(), ...init });
      if (!res.ok) return null;
      const text = await res.text();
      return text ? (JSON.parse(text) as T) : ({} as T);
    } catch {
      return null;
    }
  }

  public deduplicateCampaigns(campaigns: CampaignItem[]): CampaignItem[] {
    const map = new Map<string, CampaignItem>();
    for (const c of campaigns) if (!map.has(c.id)) map.set(c.id, c);
    return Array.from(map.values());
  }

  async fetchCampaigns(): Promise<CampaignItem[]> {
    const data = await this.request<CampaignItem[]>(`${this.apiBase}/campaigns`);
    if (data) return this.deduplicateCampaigns(data);
    const deduped = this.deduplicateCampaigns(FALLBACK_CAMPAIGNS);
    FALLBACK_CAMPAIGNS.length = 0;
    FALLBACK_CAMPAIGNS.push(...deduped);
    return [...FALLBACK_CAMPAIGNS];
  }

  async fetchProfile(): Promise<UserClaims | null> {
    return (await this.request<UserClaims>(`${this.apiBase}/profile`)) || authService.getUser() || FALLBACK_PROFILE;
  }

  async fetchCampaign(campaignId: string): Promise<CampaignItem | null> {
    const data = await this.request<CampaignItem>(`${this.apiBase}/campaigns/${campaignId}`);
    return data || FALLBACK_CAMPAIGNS.find((c) => c.id === campaignId) || createFallbackCampaign(campaignId);
  }

  async fetchCampaignMembers(campaignId: string): Promise<CampaignMember[]> {
    const data = await this.request<CampaignMember[]>(`${this.apiBase}/campaigns/${campaignId}/members`);
    return data || getFallbackCampaignMembers(campaignId);
  }

  async assignMemberRole(campaignId: string, userId: string, role: string): Promise<void> {
    const res = await this.request<void>(`${this.apiBase}/campaigns/${campaignId}/roles`, {
      method: 'POST', body: JSON.stringify({ user_id: userId, role }),
    });
    if (res !== null) return;
    assignFallbackMemberRole(campaignId, userId, role);
  }

  async createCampaignInvite(campaignId: string, role: string, expiresInHours?: number, maxUses?: number): Promise<InviteResponse> {
    const data = await this.request<InviteResponse>(`${this.apiBase}/campaigns/${campaignId}/invites`, {
      method: 'POST', body: JSON.stringify({ role, expires_in_hours: expiresInHours, max_uses: maxUses }),
    });
    return data || createFallbackInvite(campaignId, role, expiresInHours, maxUses);
  }

  async removeCampaignMember(campaignId: string, userId: string): Promise<void> {
    const res = await this.request<void>(`${this.apiBase}/campaigns/${campaignId}/members/${userId}`, { method: 'DELETE' });
    if (res !== null) return;
    removeFallbackMember(campaignId, userId);
  }

  async fetchCampaignSessions(campaignId: string): Promise<CampaignSessionItem[]> {
    const data = await this.request<any[]>(`${this.apiBase}/campaigns/${campaignId}/sessions`);
    if (data) {
      return data.map((item) => ({ ...item, campaignId: item.campaign_id || item.campaignId, participantsCount: item.participants_count ?? item.participantsCount ?? 0 }));
    }
    return getFallbackCampaignSessions(campaignId);
  }

  async fetchSession(sessionId: string): Promise<CampaignSessionItem | null> {
    const data = await this.request<any>(`${this.apiBase}/sessions/${sessionId}`);
    if (data) {
      return {
        id: data.id || sessionId, campaignId: data.campaign_id || data.campaignId || '',
        title: data.title || (sessionId === '14' || sessionId === 'session-tomb-14' ? 'Session #14' : `Session #${sessionId}`),
        status: data.status || 'active', round: data.round || 1,
        participantsCount: Array.isArray(data.participants) ? data.participants.length : (data.participantsCount || 0),
      };
    }
    return getFallbackSession(sessionId);
  }

  async fetchCharacters(): Promise<CharacterItem[]> {
    return (await this.request<CharacterItem[]>(`${this.apiBase}/characters`)) || [...FALLBACK_CHARACTERS];
  }

  getFallbackCharacterName(id: string): string | undefined {
    return FALLBACK_CHARACTERS.find((c) => c.id === id)?.name;
  }

  async fetchCharacter(characterId: string): Promise<any | null> {
    const data = await this.request<any>(`${this.apiBase}/characters/${characterId}`);
    if (data) return data;
    const char = FALLBACK_CHARACTERS.find((c) => c.id === characterId);
    return buildFallbackCharacterDetail(char, characterId);
  }

  async fetchRosterCampaignOptions(): Promise<RosterCampaignOption[]> {
    const campaigns = await this.fetchCampaigns();
    return campaigns.map((c) => ({ id: c.id, title: c.title }));
  }

  async createCharacter(payload: CreateCharacterPayload): Promise<CharacterItem> {
    const created = await this.request<CharacterItem>(`${this.apiBase}/characters`, { method: 'POST', body: JSON.stringify(payload) });
    if (created) return created;
    const newChar = createFallbackCharacter(payload, authService.getUser()?.user_id || 'user-valeros');
    FALLBACK_CHARACTERS.unshift(newChar);
    return newChar;
  }

  async assignCharacterCampaign(characterId: string, campaignId: string | null): Promise<void> {
    const res = await this.request<void>(`${this.apiBase}/characters/${characterId}/campaign`, { method: 'PATCH', body: JSON.stringify({ campaignId }) });
    if (res !== null) return;
    assignFallbackCharacterCampaign(characterId, campaignId);
  }

  async deleteCharacter(characterId: string): Promise<void> {
    const res = await this.request<void>(`${this.apiBase}/characters/${characterId}`, { method: 'DELETE' });
    if (res !== null) return;
    deleteFallbackCharacter(characterId);
  }

  async fetchLobbyState(arg1: string, arg2?: string): Promise<{ participants: LobbyParticipant[]; availableCharacters: LobbyCharacterOption[] }> {
    const isArg1Session = arg1.startsWith('session-') || arg1.startsWith('lobby-');
    const sessionId = arg2 !== undefined ? (isArg1Session ? arg1 : arg2) : arg1;
    const campaignId = arg2 !== undefined ? (isArg1Session ? arg2 : arg1) : undefined;
    const data = await this.request<any>(`${this.apiBase}/sessions/${sessionId}`);
    const participants: LobbyParticipant[] = data?.participants?.length ? data.participants : [...FALLBACK_PARTICIPANTS];
    const characters = await this.fetchCharacters();
    const availableCharacters = resolveLobbyAvailableCharacters(characters, campaignId);
    return { participants, availableCharacters };
  }

  async fetchBoardTokens(sessionId: string): Promise<BoardToken[]> {
    const data = await this.request<any>(`${this.apiBase}/boards/${sessionId}`);
    return data?.tokens || [...FALLBACK_BOARD_TOKENS];
  }

  async fetchSessionEvents(_sessionId: string): Promise<WatcherFeedEvent[]> {
    return [...FALLBACK_SESSION_EVENTS];
  }

  async createCampaignSession(campaignId: string, payload: { title: string; status?: string; scheduled_at?: string; description?: string }): Promise<CampaignSessionItem> {
    const item = await this.request<any>(`${this.apiBase}/campaigns/${campaignId}/sessions`, { method: 'POST', body: JSON.stringify(payload) });
    if (item) return { ...item, campaignId: item.campaign_id || item.campaignId, participantsCount: item.participants_count ?? item.participantsCount ?? 0 };
    return { id: `lobby-${campaignId}-${Date.now()}`, campaignId, title: payload.title, status: (payload.status as any) || 'lobby', participantsCount: 1 };
  }

  async createCampaign(payload: CreateCampaignPayload): Promise<CampaignItem> {
    let created = await this.request<CampaignItem>(`${this.apiBase}/campaigns`, { method: 'POST', body: JSON.stringify(payload) });
    if (!created) created = createFallbackCampaignItem(payload, authService.getUser()?.user_id || 'user-valeros');
    const deduped = this.deduplicateCampaigns([created, ...FALLBACK_CAMPAIGNS]);
    FALLBACK_CAMPAIGNS.length = 0;
    FALLBACK_CAMPAIGNS.push(...deduped);
    return created;
  }

  async updateCampaign(campaignId: string, payload: UpdateCampaignPayload): Promise<CampaignItem | null> {
    const data = await this.request<CampaignItem>(`${this.apiBase}/campaigns/${campaignId}`, { method: 'PATCH', body: JSON.stringify(payload) });
    if (data) return data;
    return updateFallbackCampaign(campaignId, payload);
  }
}

export const appDataService = AppDataService.getInstance();
