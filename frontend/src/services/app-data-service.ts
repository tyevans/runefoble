import type { CampaignItem, CampaignMember, CreateCampaignPayload, UpdateCampaignPayload, LobbyParticipant, LobbyCharacterOption } from '@runefoble/game-session-ui';
import type { CharacterItem, RosterCampaignOption, CreateCharacterPayload } from '@runefoble/character-sheet-ui';
import type { BoardToken } from '@runefoble/board-state-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';
import type { CampaignSessionItem } from '../components/runefoble-session-list.ts';
import { authService, type UserClaims } from '../auth/auth-service.ts';
import { resolveLobbyAvailableCharacters } from './lobby-character-options.ts';
import {
  dataFailure, dataOk, errorMessageFromBody, NETWORK_FAILURE_MESSAGE, UNREADABLE_RESPONSE_MESSAGE, type DataResult,
} from './data-result.ts';
import {
  mutateCharacterHealth, mutateCharacterEquip, mutateCharacterUnequip, mutateCharacterAddInventory,
  mutateCharacterRemoveInventory, mutateCharacterApplyCondition, mutateCharacterRemoveCondition,
  mutateCharacterCastSpell, mutateCharacterPrepareSpell, mutateCharacterRestoreSlot, mutateCharacterGuardrails,
} from './character-subresource-client.ts';

export type { DataResult } from './data-result.ts';

export interface InviteResponse {
  token: string; campaign_id: string; role: string; invite_url: string; expires_at?: string | null; created_at: string; max_uses?: number | null; uses?: number;
}

export class AppDataService {
  private static instance: AppDataService;
  public apiBase = '/api/v1';

  static getInstance(): AppDataService {
    if (!AppDataService.instance) AppDataService.instance = new AppDataService();
    return AppDataService.instance;
  }

  private getAuthHeaders(): HeadersInit {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    const token = authService.getAccessToken(), user = authService.getUser();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (user?.user_id) headers['X-User-Id'] = user.user_id;
    return headers;
  }

  /**
   * Calls the gateway. Returns a typed result. Never substitutes local data.
   * A 204 or empty body yields `{}` cast to T; callers that expect no body use DataResult<void>.
   */
  public async request<T>(path: string, init?: RequestInit): Promise<DataResult<T>> {
    const url = path.startsWith(this.apiBase) ? path : `${this.apiBase}${path}`;
    let res: Response;
    try {
      res = await fetch(url, { headers: this.getAuthHeaders(), ...init });
    } catch {
      return dataFailure(0, NETWORK_FAILURE_MESSAGE);
    }
    let text: string;
    try { text = await res.text(); } catch { return dataFailure(res.status, UNREADABLE_RESPONSE_MESSAGE); }
    let body: unknown = null;
    try { body = text ? JSON.parse(text) : null; } catch { if (res.ok && text) return dataFailure(res.status, UNREADABLE_RESPONSE_MESSAGE); }
    if (!res.ok) return dataFailure(res.status, errorMessageFromBody(body, res.status));
    return dataOk((body ?? {}) as T);
  }

  public deduplicateCampaigns(campaigns: CampaignItem[]): CampaignItem[] {
    const map = new Map<string, CampaignItem>();
    for (const c of campaigns) if (!map.has(c.id)) map.set(c.id, c);
    return Array.from(map.values());
  }

  async fetchCampaigns(): Promise<DataResult<CampaignItem[]>> {
    const res = await this.request<CampaignItem[]>(`${this.apiBase}/campaigns`);
    return res.ok ? dataOk(this.deduplicateCampaigns(res.data)) : res;
  }

  async fetchProfile(): Promise<DataResult<UserClaims>> {
    return this.request<UserClaims>(`${this.apiBase}/profile`);
  }

  async fetchCampaign(campaignId: string): Promise<DataResult<CampaignItem>> {
    return this.request<CampaignItem>(`${this.apiBase}/campaigns/${campaignId}`);
  }

  async fetchCampaignMembers(campaignId: string): Promise<DataResult<CampaignMember[]>> {
    return this.request<CampaignMember[]>(`${this.apiBase}/campaigns/${campaignId}/members`);
  }

  async assignMemberRole(campaignId: string, userId: string, role: string): Promise<DataResult<void>> {
    return this.request<void>(`${this.apiBase}/campaigns/${campaignId}/roles`, { method: 'POST', body: JSON.stringify({ user_id: userId, role }) });
  }

  async createCampaignInvite(campaignId: string, role: string, expiresInHours?: number, maxUses?: number): Promise<DataResult<InviteResponse>> {
    return this.request<InviteResponse>(`${this.apiBase}/campaigns/${campaignId}/invites`, { method: 'POST', body: JSON.stringify({ role, expires_in_hours: expiresInHours, max_uses: maxUses }) });
  }

  async removeCampaignMember(campaignId: string, userId: string): Promise<DataResult<void>> {
    return this.request<void>(`${this.apiBase}/campaigns/${campaignId}/members/${userId}`, { method: 'DELETE' });
  }

  async fetchCampaignSessions(campaignId: string): Promise<DataResult<CampaignSessionItem[]>> {
    const res = await this.request<any[]>(`${this.apiBase}/campaigns/${campaignId}/sessions`);
    if (!res.ok) return res;
    return dataOk(res.data.map((item) => this.toSessionItem(item)));
  }

  async fetchSession(sessionId: string): Promise<DataResult<CampaignSessionItem>> {
    const res = await this.request<any>(`${this.apiBase}/sessions/${sessionId}`);
    if (!res.ok) return res;
    const data = res.data;
    return dataOk({
      id: data.id || sessionId,
      campaignId: data.campaign_id || data.campaignId || '',
      title: data.title || `Session #${sessionId}`,
      status: data.status || 'active',
      round: data.round || 1,
      participantsCount: Array.isArray(data.participants) ? data.participants.length : (data.participantsCount || 0),
    });
  }

  private toSessionItem(item: any): CampaignSessionItem {
    return { ...item, campaignId: item.campaign_id || item.campaignId, participantsCount: item.participants_count ?? item.participantsCount ?? 0 };
  }

  async fetchCharacters(): Promise<DataResult<CharacterItem[]>> { return this.request<CharacterItem[]>(`${this.apiBase}/characters`); }

  async fetchCharacter(characterId: string): Promise<DataResult<any>> { return this.request<any>(`${this.apiBase}/characters/${characterId}`); }

  async modifyCharacterHealth(characterId: string, delta: number, source = 'damage'): Promise<DataResult<any>> {
    return mutateCharacterHealth(this, characterId, delta, source);
  }
  equipCharacterItem(characterId: string, slot: string, itemName: string | null): Promise<DataResult<any>> { return mutateCharacterEquip(this, characterId, slot, itemName || ''); }
  unequipCharacterItem(characterId: string, slot: string): Promise<DataResult<any>> { return mutateCharacterUnequip(this, characterId, slot); }
  addCharacterInventoryItem(characterId: string, item: any): Promise<DataResult<any>> { return mutateCharacterAddInventory(this, characterId, item); }
  removeCharacterInventoryItem(characterId: string, itemId: string, quantity = 1): Promise<DataResult<any>> { return mutateCharacterRemoveInventory(this, characterId, itemId, quantity); }
  applyCharacterCondition(characterId: string, condition: string, source = 'tactical'): Promise<DataResult<any>> { return mutateCharacterApplyCondition(this, characterId, condition, source); }
  removeCharacterCondition(characterId: string, condition: string): Promise<DataResult<any>> { return mutateCharacterRemoveCondition(this, characterId, condition); }
  castCharacterSpell(characterId: string, spellName: string, slotLevel = 1): Promise<DataResult<any>> { return mutateCharacterCastSpell(this, characterId, spellName, slotLevel); }
  prepareCharacterSpell(characterId: string, spellName: string, isPrepared = true): Promise<DataResult<any>> { return mutateCharacterPrepareSpell(this, characterId, spellName, isPrepared); }
  restoreCharacterSpellSlot(characterId: string, slotLevel: number): Promise<DataResult<any>> { return mutateCharacterRestoreSlot(this, characterId, slotLevel); }
  updateCharacterGuardrails(characterId: string, payload: any): Promise<DataResult<any>> { return mutateCharacterGuardrails(this, characterId, payload); }

  async fetchRosterCampaignOptions(): Promise<DataResult<RosterCampaignOption[]>> {
    const res = await this.fetchCampaigns();
    return res.ok ? dataOk(res.data.map((c) => ({ id: c.id, title: c.title }))) : res;
  }

  async createCharacter(payload: CreateCharacterPayload): Promise<DataResult<CharacterItem>> {
    return this.request<CharacterItem>(`${this.apiBase}/characters`, { method: 'POST', body: JSON.stringify(payload) });
  }

  async assignCharacterCampaign(characterId: string, campaignId: string | null): Promise<DataResult<void>> {
    return this.request<void>(`${this.apiBase}/characters/${characterId}/campaign`, { method: 'PATCH', body: JSON.stringify({ campaignId }) });
  }

  async deleteCharacter(characterId: string): Promise<DataResult<void>> {
    return this.request<void>(`${this.apiBase}/characters/${characterId}`, { method: 'DELETE' });
  }

  async fetchLobbyState(arg1: string, arg2?: string): Promise<DataResult<{ participants: LobbyParticipant[]; availableCharacters: LobbyCharacterOption[] }>> {
    const isArg1Session = arg1.startsWith('session-') || arg1.startsWith('lobby-');
    const sessionId = arg2 !== undefined ? (isArg1Session ? arg1 : arg2) : arg1;
    const campaignId = arg2 !== undefined ? (isArg1Session ? arg2 : arg1) : undefined;
    const session = await this.request<any>(`${this.apiBase}/sessions/${sessionId}`);
    if (!session.ok) return session;
    const characters = await this.fetchCharacters();
    if (!characters.ok) return characters;
    const participants: LobbyParticipant[] = Array.isArray(session.data?.participants) ? session.data.participants : [];
    return dataOk({ participants, availableCharacters: resolveLobbyAvailableCharacters(characters.data, campaignId) });
  }

  async fetchBoardState(sessionId: string): Promise<DataResult<{ cols: number; rows: number; tokens: BoardToken[] }>> {
    const res = await this.request<any>(`${this.apiBase}/boards/${sessionId}`);
    if (!res.ok) return res;
    return dataOk({ cols: res.data?.cols ?? 10, rows: res.data?.rows ?? 10, tokens: res.data?.tokens || [] });
  }

  async fetchBoardTokens(sessionId: string): Promise<DataResult<BoardToken[]>> {
    const res = await this.fetchBoardState(sessionId);
    return res.ok ? dataOk(res.data.tokens) : res;
  }

  /** No session-event read endpoint exists yet. The feed starts empty and fills from live WebSocket events. */
  async fetchSessionEvents(_sessionId: string): Promise<DataResult<WatcherFeedEvent[]>> { return dataOk([]); }

  async createCampaignSession(campaignId: string, payload: { title: string; status?: string; scheduled_at?: string; scheduledAt?: string; description?: string }): Promise<DataResult<CampaignSessionItem>> {
    const res = await this.request<any>(`${this.apiBase}/campaigns/${campaignId}/sessions`, { method: 'POST', body: JSON.stringify(payload) });
    return res.ok ? dataOk(this.toSessionItem(res.data)) : res;
  }

  async createCampaign(payload: CreateCampaignPayload): Promise<DataResult<CampaignItem>> {
    return this.request<CampaignItem>(`${this.apiBase}/campaigns`, { method: 'POST', body: JSON.stringify(payload) });
  }

  async updateCampaign(campaignId: string, payload: UpdateCampaignPayload): Promise<DataResult<CampaignItem>> {
    return this.request<CampaignItem>(`${this.apiBase}/campaigns/${campaignId}`, { method: 'PATCH', body: JSON.stringify(payload) });
  }

  async requestHotSwap(sessionId: string, characterId: string, playerId?: string): Promise<DataResult<any>> {
    const pid = playerId || authService.getUser()?.user_id || '';
    return this.request<any>(`${this.apiBase}/sessions/${sessionId}/hot-swap`, { method: 'POST', body: JSON.stringify({ sessionId, characterId, playerId: pid }) });
  }

  async updateProfile(payload: UpdateProfilePayload): Promise<DataResult<UserClaims>> {
    const cur = authService.getUser();
    if (!cur) return dataFailure(401, 'Sign in to update your profile.');
    const res = await this.request<UserClaims>(`${this.apiBase}/profile`, { method: 'PATCH', body: JSON.stringify(payload) });
    if (!res.ok) return res;
    const data = res.data;
    const updated: UserClaims = { ...cur, ...data, display_name: payload.displayName ?? data.display_name ?? cur.display_name, avatar_url: payload.avatarUrl ?? data.avatar_url ?? cur.avatar_url, bio: payload.bio ?? data.bio ?? cur.bio };
    authService.updateUser(updated);
    return dataOk(updated);
  }
}

export interface UpdateProfilePayload { displayName?: string; avatarUrl?: string; bio?: string; email?: string; }

export const appDataService = AppDataService.getInstance();
