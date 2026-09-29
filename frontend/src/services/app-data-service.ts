import type { CampaignItem, CampaignMember, CreateCampaignPayload, UpdateCampaignPayload, LobbyParticipant, LobbyCharacterOption } from '@runefoble/game-session-ui';
import type { CharacterItem, RosterCampaignOption, CreateCharacterPayload } from '@runefoble/character-sheet-ui';
import type { BoardToken } from '@runefoble/board-state-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';
import type { CampaignSessionItem } from '../components/runefoble-session-list.ts';
import { authService, type UserClaims } from '../auth/auth-service.ts';
import { getOrCreateFallbackCharacterDetail, FALLBACK_CHARACTER_DETAILS_CACHE } from './fallback-data.ts';
import {
  FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS, FALLBACK_MEMBERS, FALLBACK_PARTICIPANTS,
  FALLBACK_SESSIONS, FALLBACK_PROFILE, FALLBACK_BOARD_TOKENS, FALLBACK_SESSION_EVENTS,
  FALLBACK_CAMPAIGN_SESSIONS_MAP, getFallbackCampaignSessions, getFallbackSession, createFallbackCampaign,
  createFallbackCampaignItem, updateFallbackCampaign, createFallbackCharacter,
  assignFallbackCharacterCampaign, deleteFallbackCharacter, resolveLobbyAvailableCharacters,
} from './app-data-service.fixtures.ts';
import {
  mutateCharacterHealth, mutateCharacterEquip, mutateCharacterUnequip,
  mutateCharacterAddInventory, mutateCharacterRemoveInventory, mutateCharacterApplyCondition,
  mutateCharacterRemoveCondition, mutateCharacterCastSpell, mutateCharacterPrepareSpell,
  mutateCharacterRestoreSlot, mutateCharacterGuardrails,
} from './character-subresource-client.ts';

export { FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS, FALLBACK_MEMBERS, FALLBACK_PARTICIPANTS, FALLBACK_SESSIONS, FALLBACK_CAMPAIGN_SESSIONS_MAP };

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

  public async request<T>(path: string, init?: RequestInit): Promise<T | null> {
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
    return (await this.request<CampaignMember[]>(`${this.apiBase}/campaigns/${campaignId}/members`)) || [...FALLBACK_MEMBERS];
  }

  async fetchCampaignSessions(campaignId: string): Promise<CampaignSessionItem[]> {
    const data = await this.request<any[]>(`${this.apiBase}/campaigns/${campaignId}/sessions`);
    if (data) return data.map((item) => ({ ...item, campaignId: item.campaign_id || item.campaignId, participantsCount: item.participants_count ?? item.participantsCount ?? 0 }));
    return getFallbackCampaignSessions(campaignId);
  }

  async fetchSession(sessionId: string): Promise<CampaignSessionItem | null> {
    const data = await this.request<any>(`${this.apiBase}/sessions/${sessionId}`);
    if (data) return { id: data.id || sessionId, campaignId: data.campaign_id || data.campaignId || '', title: data.title || (sessionId === '14' || sessionId === 'session-tomb-14' ? 'Session #14' : `Session #${sessionId}`), status: data.status || 'active', round: data.round || 1, participantsCount: Array.isArray(data.participants) ? data.participants.length : (data.participantsCount || 0) };
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
    if (data) { FALLBACK_CHARACTER_DETAILS_CACHE.set(characterId, data); return data; }
    const char = FALLBACK_CHARACTERS.find((c) => c.id === characterId);
    return getOrCreateFallbackCharacterDetail(char, characterId);
  }

  getFallbackCharacterDetail(characterId: string): any {
    const char = FALLBACK_CHARACTERS.find((c) => c.id === characterId);
    return getOrCreateFallbackCharacterDetail(char, characterId);
  }

  async modifyCharacterHealth(characterId: string, delta: number, source = 'damage'): Promise<any> {
    const res = await mutateCharacterHealth(this, characterId, delta, source);
    const fc = FALLBACK_CHARACTERS.find((c) => c.id === characterId);
    if (fc && res?.current_hp !== undefined) fc.currentHp = res.current_hp;
    return res;
  }
  modifyCharacterHealthSync(characterId: string, delta: number, source = 'damage'): any { return mutateCharacterHealth(this, characterId, delta, source); }
  equipCharacterItem(characterId: string, slot: string, itemName: string | null): Promise<any> { return mutateCharacterEquip(this, characterId, slot, itemName || ''); }
  unequipCharacterItem(characterId: string, slot: string): Promise<any> { return mutateCharacterUnequip(this, characterId, slot); }
  addCharacterInventoryItem(characterId: string, item: any): Promise<any> { return mutateCharacterAddInventory(this, characterId, item); }
  removeCharacterInventoryItem(characterId: string, itemId: string, quantity = 1): Promise<any> { return mutateCharacterRemoveInventory(this, characterId, itemId, quantity); }
  applyCharacterCondition(characterId: string, condition: string, source = 'tactical'): Promise<any> { return mutateCharacterApplyCondition(this, characterId, condition, source); }
  removeCharacterCondition(characterId: string, condition: string): Promise<any> { return mutateCharacterRemoveCondition(this, characterId, condition); }
  castCharacterSpell(characterId: string, spellName: string, slotLevel = 1): Promise<any> { return mutateCharacterCastSpell(this, characterId, spellName, slotLevel); }
  prepareCharacterSpell(characterId: string, spellName: string, isPrepared = true): Promise<any> { return mutateCharacterPrepareSpell(this, characterId, spellName, isPrepared); }
  restoreCharacterSpellSlot(characterId: string, slotLevel: number): Promise<any> { return mutateCharacterRestoreSlot(this, characterId, slotLevel); }
  updateCharacterGuardrails(characterId: string, payload: any): Promise<any> { return mutateCharacterGuardrails(this, characterId, payload); }
  async fetchRosterCampaignOptions(): Promise<RosterCampaignOption[]> { return (await this.fetchCampaigns()).map((c) => ({ id: c.id, title: c.title })); }

  async createCharacter(payload: CreateCharacterPayload): Promise<CharacterItem> {
    const created = await this.request<CharacterItem>(`${this.apiBase}/characters`, { method: 'POST', body: JSON.stringify(payload) });
    if (created) return created;
    const newChar = createFallbackCharacter(payload, authService.getUser()?.user_id || 'user-valeros');
    FALLBACK_CHARACTERS.unshift(newChar);
    return newChar;
  }

  async assignCharacterCampaign(characterId: string, campaignId: string | null): Promise<void> {
    if ((await this.request<void>(`${this.apiBase}/characters/${characterId}/campaign`, { method: 'PATCH', body: JSON.stringify({ campaignId }) })) === null) assignFallbackCharacterCampaign(characterId, campaignId);
  }

  async deleteCharacter(characterId: string): Promise<void> {
    if ((await this.request<void>(`${this.apiBase}/characters/${characterId}`, { method: 'DELETE' })) === null) deleteFallbackCharacter(characterId);
  }

  async fetchLobbyState(arg1: string, arg2?: string): Promise<{ participants: LobbyParticipant[]; availableCharacters: LobbyCharacterOption[] }> {
    const isArg1Session = arg1.startsWith('session-') || arg1.startsWith('lobby-');
    const sessionId = arg2 !== undefined ? (isArg1Session ? arg1 : arg2) : arg1;
    const campaignId = arg2 !== undefined ? (isArg1Session ? arg2 : arg1) : undefined;
    const data = await this.request<any>(`${this.apiBase}/sessions/${sessionId}`);
    const participants: LobbyParticipant[] = data?.participants?.length ? data.participants : [...FALLBACK_PARTICIPANTS];
    const characters = await this.fetchCharacters();
    return { participants, availableCharacters: resolveLobbyAvailableCharacters(characters, campaignId) };
  }

  async fetchBoardTokens(sessionId: string): Promise<BoardToken[]> {
    return (await this.request<any>(`${this.apiBase}/boards/${sessionId}`))?.tokens || [...FALLBACK_BOARD_TOKENS];
  }

  async fetchSessionEvents(_sessionId: string): Promise<WatcherFeedEvent[]> {
    return [...FALLBACK_SESSION_EVENTS];
  }

  async createCampaignSession(campaignId: string, payload: { title: string; status?: string; scheduled_at?: string; scheduledAt?: string; description?: string }): Promise<CampaignSessionItem> {
    const item = await this.request<any>(`${this.apiBase}/campaigns/${campaignId}/sessions`, { method: 'POST', body: JSON.stringify(payload) });
    if (item) return { ...item, campaignId: item.campaign_id || item.campaignId, participantsCount: item.participants_count ?? item.participantsCount ?? 0 };
    if (!FALLBACK_CAMPAIGN_SESSIONS_MAP[campaignId]) getFallbackCampaignSessions(campaignId);
    const newSession: CampaignSessionItem = { id: `lobby-${campaignId}-${Date.now()}`, campaignId, title: payload.title, status: (payload.status as any) || 'lobby', round: 1, participantsCount: 1, scheduled_at: payload.scheduled_at || payload.scheduledAt, description: payload.description || '' };
    FALLBACK_CAMPAIGN_SESSIONS_MAP[campaignId].push(newSession);
    return newSession;
  }

  async createCampaign(payload: CreateCampaignPayload): Promise<CampaignItem> {
    const created = (await this.request<CampaignItem>(`${this.apiBase}/campaigns`, { method: 'POST', body: JSON.stringify(payload) })) || createFallbackCampaignItem(payload);
    const deduped = this.deduplicateCampaigns([created, ...FALLBACK_CAMPAIGNS]);
    FALLBACK_CAMPAIGNS.length = 0; FALLBACK_CAMPAIGNS.push(...deduped);
    return created;
  }

  async updateCampaign(campaignId: string, payload: UpdateCampaignPayload): Promise<CampaignItem | null> {
    const data = await this.request<CampaignItem>(`${this.apiBase}/campaigns/${campaignId}`, { method: 'PATCH', body: JSON.stringify(payload) });
    return data || updateFallbackCampaign(campaignId, payload);
  }

  async requestHotSwap(sessionId: string, characterId: string, playerId?: string): Promise<any> {
    const pid = playerId || authService.getUser()?.user_id || 'user-valeros';
    const data = await this.request<any>(`${this.apiBase}/sessions/${sessionId}/hot-swap`, {
      method: 'POST', body: JSON.stringify({ sessionId, characterId, playerId: pid }),
    });
    return data || { session_id: sessionId, character_id: characterId, player_id: pid, status: 'control_transferred' };
  }

  async updateProfile(payload: UpdateProfilePayload): Promise<UserClaims | null> {
    const data = await this.request<UserClaims>(`${this.apiBase}/profile`, { method: 'PATCH', body: JSON.stringify(payload) });
    const cur = authService.getUser() || FALLBACK_PROFILE;
    const updated: UserClaims = {
      ...cur, ...(data || {}),
      display_name: payload.displayName ?? data?.display_name ?? cur.display_name,
      avatar_url: payload.avatarUrl ?? data?.avatar_url ?? cur.avatar_url,
      bio: payload.bio ?? data?.bio ?? cur.bio,
    };
    authService.updateUser(updated);
    return updated;
  }
}

export interface UpdateProfilePayload {
  displayName?: string;
  avatarUrl?: string;
  bio?: string;
  email?: string;
}

export const appDataService = AppDataService.getInstance();

