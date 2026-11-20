import type { CampaignItem, CampaignMember, CreateCampaignPayload, UpdateCampaignPayload, LobbyCharacterOption, LobbyParticipant } from '@runefoble/game-session-ui';
import type { CharacterItem, RosterCampaignOption, CreateCharacterPayload } from '@runefoble/character-sheet-ui';
import type { PartySeat } from '@runefoble/board-state-ui';
import type { CaravanContractItem } from '@runefoble/game-session-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';
import type { CampaignSessionItem } from '../components/runefoble-session-list.ts';
import { authService, type UserClaims } from '../auth/auth-service.ts';
import { toWatcherFeedEvent, type SessionChronicleEntry } from './session-chronicle.ts';
import { resolveLobbyAvailableCharacters } from './lobby-character-options.ts';
import type { CampaignCapabilities } from './campaign-capabilities.ts';
import { dataFailure, dataOk, isNotFound, type DataResult } from './data-result.ts';
import type { SessionBoard } from './session-board.ts';
import { requestData } from './shell-request.ts';
import { isArray, isString, malformedResponse, requireFields } from './required-fields.ts';
import {
  SESSION_REQUIRED_FIELDS, sessionFromOwner, lobbyParticipantsFromOwner, boardFromOwner, sessionSeatsFromOwner,
} from './owner-wire-mappers.ts';
import type { RequestSpec } from '@runefoble/ui-core';
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

  /**
   * Calls the gateway through the shared transport. Returns a typed result. Never substitutes
   * local data. A 204 or empty body yields `{}` cast to T; callers that expect no body use DataResult<void>.
   */
  public request<T>(path: string, spec?: RequestSpec): Promise<DataResult<T>> {
    const url = path.startsWith(this.apiBase) ? path : `${this.apiBase}${path}`;
    return requestData<T>(url, spec);
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

  async fetchCampaignCapabilities(campaignId: string): Promise<DataResult<CampaignCapabilities>> {
    return this.request<CampaignCapabilities>(`${this.apiBase}/campaigns/${campaignId}/capabilities`);
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
    if (!isArray(res.data)) return malformedResponse('the session list is not a list');
    const items: CampaignSessionItem[] = [];
    for (const item of res.data) {
      const mapped = this.toSessionItem(item);
      if (!mapped.ok) return mapped;
      items.push(mapped.data);
    }
    return dataOk(items);
  }

  /** Reads the caravan notice board of a shared world through the gateway (TASK-0807). */
  async fetchCaravanContracts(sharedWorldId: string): Promise<DataResult<CaravanContractItem[]>> {
    const res = await this.request<{ contracts: CaravanContractItem[] }>(`${this.apiBase}/shared-worlds/${sharedWorldId}/caravans/contracts`);
    if (!res.ok) return res;
    if (!isArray(res.data.contracts)) return malformedResponse('contracts is not a list');
    return dataOk(res.data.contracts);
  }

  async fetchSession(sessionId: string): Promise<DataResult<CampaignSessionItem>> {
    const res = await this.request<any>(`${this.apiBase}/sessions/${sessionId}`);
    if (!res.ok) return res;
    return sessionFromOwner(res.data);
  }

  private toSessionItem(item: any): DataResult<CampaignSessionItem> {
    return requireFields({
      ...item,
      campaignId: item?.campaign_id || item?.campaignId,
      participantsCount: item?.participants_count ?? item?.participantsCount ?? 0,
    }, SESSION_REQUIRED_FIELDS);
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

  async fetchLobbyState(campaignId: string, sessionId: string): Promise<DataResult<{ participants: LobbyParticipant[]; availableCharacters: LobbyCharacterOption[] }>> {
    const session = await this.request<any>(`${this.apiBase}/sessions/${sessionId}`);
    if (!session.ok) return session;
    const members = await this.fetchCampaignMembers(campaignId);
    if (!members.ok) return members;
    const characters = await this.fetchCharacters();
    if (!characters.ok) return characters;
    const roster = lobbyParticipantsFromOwner(session.data, members.data);
    if (!roster.ok) return roster;
    return dataOk({ participants: roster.data, availableCharacters: resolveLobbyAvailableCharacters(characters.data, campaignId) });
  }

  /** Seats the verified caller in the lobby through the gateway join route (TASK-0889). */
  async joinSession(sessionId: string, seat: { character_id: string; character_name: string; character_class: string }): Promise<DataResult<unknown>> {
    return this.request<unknown>(`${this.apiBase}/sessions/${sessionId}/join`, { method: 'POST', body: JSON.stringify(seat) });
  }

  /** Records the verified caller's lobby character through the gateway route (TASK-0952). */
  async selectLobbyCharacter(sessionId: string, characterId: string): Promise<DataResult<unknown>> {
    return this.request<unknown>(`${this.apiBase}/sessions/${sessionId}/lobby/character`, { method: 'POST', body: JSON.stringify({ character_id: characterId }) });
  }

  /** Stores the verified caller's lobby readiness through the gateway route (TASK-0952). */
  async setLobbyReadiness(sessionId: string, isReady: boolean): Promise<DataResult<unknown>> {
    return this.request<unknown>(`${this.apiBase}/sessions/${sessionId}/lobby/readiness`, { method: 'POST', body: JSON.stringify({ is_ready: isReady }) });
  }

  /**
   * Sets or releases the AI stand-in of one seat (TASK-0952). A player sets their own seat. The DM
   * sets any seat. game_session checks both and answers 403 for any other caller.
   */
  async setSeatStandIn(sessionId: string, userId: string, isAbsent: boolean): Promise<DataResult<unknown>> {
    return this.request<unknown>(`${this.apiBase}/sessions/${sessionId}/seats/${userId}/stand-in`, { method: 'POST', body: JSON.stringify({ is_absent: isAbsent }) });
  }

  /**
   * Moves a lobby session to `active` through the gateway start route (TASK-0910). game_session
   * checks `session.control`. The gateway then sends `session_started` to every session socket.
   */
  async startSession(sessionId: string): Promise<DataResult<{ status: string }>> {
    const res = await this.request<{ status: string }>(`${this.apiBase}/sessions/${sessionId}/start`, { method: 'POST' });
    return res.ok ? requireFields(res.data, { status: isString }) : res;
  }

  /**
   * Moves an active session to `ended` through the gateway end route (TASK-0953). game_session
   * checks `session.control` and refuses an end from any status but `active`. The gateway then
   * sends `session_ended` to every session socket.
   */
  async endSession(sessionId: string): Promise<DataResult<{ status: string }>> {
    const res = await this.request<{ status: string }>(`${this.apiBase}/sessions/${sessionId}/end`, { method: 'POST' });
    return res.ok ? requireFields(res.data, { status: isString }) : res;
  }

  /** Reads the status of a session (`lobby`, `active` or `ended`) from the owner state (TASK-0953). */
  async fetchSessionStatus(sessionId: string): Promise<DataResult<string>> {
    const res = await this.request<{ status: string }>(`${this.apiBase}/sessions/${sessionId}`);
    if (!res.ok) return res;
    const checked = requireFields(res.data, { status: isString });
    return checked.ok ? dataOk(checked.data.status) : checked;
  }

  /**
   * Reads the session board (TASK-0906). A 404 means that no board exists yet for the session.
   * It gives the typed `no_board` state. Every other failure stays a failure.
   */
  async fetchBoardState(sessionId: string): Promise<DataResult<SessionBoard>> {
    const res = await this.request<any>(`${this.apiBase}/boards/${sessionId}`);
    if (isNotFound(res)) return dataOk({ kind: 'no_board' });
    if (!res.ok) return res;
    const board = boardFromOwner(res.data);
    return board.ok ? dataOk({ kind: 'board', ...board.data }) : board;
  }

  /** Reads the seated characters of a session, for the battlemap set-up (TASK-0922). */
  async fetchSessionSeats(sessionId: string): Promise<DataResult<PartySeat[]>> {
    const res = await this.request<any>(`${this.apiBase}/sessions/${sessionId}`);
    return res.ok ? sessionSeatsFromOwner(res.data) : res;
  }

  /** Reads the session chronicle feed from the gateway (TASK-0641). An empty session yields []. */
  async fetchSessionEvents(sessionId: string): Promise<DataResult<WatcherFeedEvent[]>> {
    const res = await this.request<SessionChronicleEntry[]>(`${this.apiBase}/sessions/${sessionId}/events`);
    return res.ok ? dataOk(res.data.map(toWatcherFeedEvent)) : res;
  }

  async createCampaignSession(campaignId: string, payload: { title: string; status?: string; scheduled_at?: string; scheduledAt?: string; description?: string }): Promise<DataResult<CampaignSessionItem>> {
    const res = await this.request<any>(`${this.apiBase}/campaigns/${campaignId}/sessions`, { method: 'POST', body: JSON.stringify(payload) });
    return res.ok ? this.toSessionItem(res.data) : res;
  }

  async createCampaign(payload: CreateCampaignPayload): Promise<DataResult<CampaignItem>> {
    return this.request<CampaignItem>(`${this.apiBase}/campaigns`, { method: 'POST', body: JSON.stringify(payload) });
  }

  async updateCampaign(campaignId: string, payload: UpdateCampaignPayload): Promise<DataResult<CampaignItem>> {
    return this.request<CampaignItem>(`${this.apiBase}/campaigns/${campaignId}`, { method: 'PATCH', body: JSON.stringify(payload) });
  }

  async requestHotSwap(sessionId: string, characterId: string): Promise<DataResult<any>> {
    return this.request<any>(`${this.apiBase}/sessions/${sessionId}/hot-swap`, { method: 'POST', body: JSON.stringify({ sessionId, characterId }) });
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
