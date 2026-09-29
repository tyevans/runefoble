import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import './styles/themes.css';
import { appShellStyles } from './styles/app-shell.styles.ts';
import './components/runefoble-header.ts'; import './components/runefoble-settings-modal.ts'; import './components/runefoble-auth-modal.ts'; import './components/runefoble-session-list.ts'; import './components/plugins/runefoble-plugin-slot.ts'; import './components/runefoble-user-profile.ts';

import '@runefoble/board-state-ui'; import '@runefoble/character-sheet-ui'; import '@runefoble/game-session-ui'; import '@runefoble/the-watcher-ui'; import '@runefoble/voice-agent-ui';
import type { BoardToken } from '@runefoble/board-state-ui'; import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';
import type { CampaignItem, CampaignMember, CreateCampaignPayload, UpdateCampaignPayload, LobbyParticipant, LobbyCharacterOption } from '@runefoble/game-session-ui';
import type { CharacterItem, RosterCampaignOption, CreateCharacterPayload, AssignCampaignEventDetail, DeleteCharacterEventDetail, InspectCharacterEventDetail } from '@runefoble/character-sheet-ui';
import type { CampaignSessionItem } from './components/runefoble-session-list.ts';
import { router, registerAuthGuard, type BreadcrumbItem, type MatchedRoute, type RouteParams } from './router/index.ts';
import { authService, type AuthState } from './auth/auth-service.ts';
import { appDataService } from './services/app-data-service.ts';
import {
  handleSheetHpChange, handleSheetEquipItem, handleSheetUnequipItem, handleSheetAddItem, handleSheetRemoveItem,
  handleSheetCastSpell, handleSheetPrepareSpell, handleSheetApplyCondition, handleSheetRemoveCondition, handleSheetExpendSlot, handleSheetRestoreSlot,
} from './character-sheet-handlers.ts';

export type AppActiveView = 'login' | 'campaigns' | 'campaign-detail' | 'campaign-characters' | 'characters' | 'character-sheet' | 'session-lobby' | 'session-active' | 'profile';

@customElement('runefoble-app')
export class RunefobleApp extends LitElement {
  static styles = [appShellStyles];

  @state() private viewMode: 'party' | 'spectator' = 'party'; @state() private isSettingsOpen = false;
  @state() private currentTheme = 'bauhaus'; @state() private currentColorMode: 'light' | 'dark' | 'system' = 'system';
  @state() private isListening = false; @state() private socketConnected = false;
  @state() private campaignId = '4'; @state() private sessionId = 'session-tomb-14';
  @state() private campaignTitle = 'Tomb of the Star-Eater'; @state() private sessionTitle = 'Session #14';
  @state() private selectedCharacterId = ''; @state() private selectedCharacter: any = null;
  @state() private tokens: BoardToken[] = []; @state() private events: WatcherFeedEvent[] = [];
  @state() private breadcrumbs: BreadcrumbItem[] = []; @state() private currentRoute: MatchedRoute | null = null;
  @state() public routeParams: RouteParams = {}; @state() private isAuthModalOpen = false;
  @state() private authInitialTab: 'login' | 'register' = 'login';
  @state() private currentUserId = 'user-valeros'; @state() private userRole = 'Player'; @state() private isDM = false;
  @state() private campaigns: CampaignItem[] = []; @state() private currentCampaign: CampaignItem | null = null;
  @state() private campaignMembers: CampaignMember[] = []; @state() private campaignSessions: CampaignSessionItem[] = [];
  @state() private characters: CharacterItem[] = []; @state() private rosterCampaigns: RosterCampaignOption[] = [];
  @state() private lobbyParticipants: LobbyParticipant[] = []; @state() private lobbyAvailableCharacters: LobbyCharacterOption[] = [];
  @state() public activeCharacter: CharacterItem | null = null;
  @state() private toastMessage: string | null = null;
  private toastTimeout: ReturnType<typeof setTimeout> | null = null;

  private socket: WebSocket | null = null; private activeSocketSessionId: string | null = null; private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private unlistenRouter: (() => void) | null = null; private unlistenAuth: (() => void) | null = null; private unlistenTeardown: (() => void) | null = null; private unlistenGuard: (() => void) | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.initTheme(); this.syncAuthState(authService.getState());
    this.unlistenAuth = authService.onAuthChanged((s) => this.syncAuthState(s));
    this.initRouter();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.unlistenRouter?.(); this.unlistenAuth?.(); this.unlistenTeardown?.(); this.unlistenGuard?.();
    this.disconnectWebSocket();
    if (this.toastTimeout) { clearTimeout(this.toastTimeout); this.toastTimeout = null; }
    router.stop();
  }

  public getActiveView(): AppActiveView {
    const pat = this.currentRoute?.pattern || '';
    if (pat === '#/login' || pat === '#/register') return 'login';
    if (pat.startsWith('#/campaigns/:campaignId/lobby/')) return 'session-lobby';
    if (pat.startsWith('#/campaigns/:campaignId/sessions/')) return 'session-active';
    if (pat === '#/campaigns/:campaignId/characters') return 'campaign-characters';
    if (pat.startsWith('#/campaigns/:campaignId')) return 'campaign-detail';
    if (pat.startsWith('#/characters/') && pat !== '#/characters') return 'character-sheet';
    if (pat === '#/characters') return 'characters';
    return pat === '#/profile' ? 'profile' : 'campaigns';
  }

  private syncAuthState(s: AuthState) {
    this.currentUserId = s.user?.user_id || 'user-valeros';
    this.isDM = Boolean(s.user?.roles.some((r) => ['dm', 'admin', 'owner'].includes(r)));
    this.userRole = this.isDM ? 'Dungeon Master' : 'Player';
  }

  private initTheme() {
    try {
      this.currentTheme = window?.localStorage?.getItem('runefoble-theme') || this.currentTheme;
      this.currentColorMode = (window?.localStorage?.getItem('runefoble-color-mode') as any) || this.currentColorMode;
    } catch { /* storage restricted */ }
    document?.documentElement?.setAttribute('data-theme', this.currentTheme); document?.documentElement?.setAttribute('data-color-mode', this.currentColorMode);
  }

  private initRouter() {
    this.unlistenGuard = registerAuthGuard(router, authService);
    router.setTitleResolver((type, id) => {
      if (type === 'campaign') return id === '4' ? 'Tomb of the Star-Eater' : id === '5' ? 'Whispering Depths' : undefined;
      if (type === 'character') return this.characters.find((c) => c.id === id)?.name || appDataService.getFallbackCharacterName(id);
      return (type === 'session' && (id === '14' || id === 'session-tomb-14')) ? 'Session #14' : type === 'lobby' ? `Lobby ${id}` : undefined;
    });
    router.setAsyncTitleResolver(async (type, id) => {
      if (type === 'campaign') return (await appDataService.fetchCampaign(id))?.title;
      if (type === 'character') return (await appDataService.fetchCharacter(id))?.name;
      if (type === 'session' || type === 'lobby') return (await appDataService.fetchSession(id))?.title;
      return undefined;
    });
    this.unlistenTeardown = router.registerTeardown(() => { const p = router.getCurrentRoute()?.pattern || ''; if (!p.includes('/sessions/') && !p.includes('/lobby/')) this.disconnectWebSocket(); });
    this.unlistenRouter = router.onRouteChanged((r) => this.handleRouteChanged(r));
    router.start();
    const cur = router.getCurrentRoute();
    if (cur) this.handleRouteChanged(cur);
  }

  private async handleRouteChanged(route: MatchedRoute) {
    this.currentRoute = route; this.routeParams = route.params; this.breadcrumbs = route.breadcrumbs;
    if (route.params.campaignId) { this.campaignId = route.params.campaignId; this.campaignTitle = router.resolveTitle('campaign', this.campaignId) || `Campaign #${this.campaignId}`; }
    if (route.params.sessionId) { this.sessionId = route.params.sessionId; this.sessionTitle = router.resolveTitle('session', this.sessionId) || router.resolveTitle('lobby', this.sessionId) || `Session #${this.sessionId}`; }
    if (route.params.characterId) { this.selectedCharacterId = route.params.characterId; }
    if (route.pattern === '#/login' || route.pattern === '#/register') { this.authInitialTab = route.pattern === '#/register' ? 'register' : 'login'; this.isAuthModalOpen = true; }
    this.manageWebSocketLifecycle(route); await this.loadRouteData(route);
  }

  private manageWebSocketLifecycle(route: MatchedRoute) {
    if (route.pattern.includes('/sessions/') || route.pattern.includes('/lobby/')) {
      const target = route.params.sessionId || this.sessionId;
      if (!this.socket || this.activeSocketSessionId !== target) this.connectWebSocket(target);
    } else this.disconnectWebSocket();
  }

  private connectWebSocket(sessionId: string) {
    this.disconnectWebSocket();
    this.activeSocketSessionId = sessionId;
    try {
      if (typeof window === 'undefined' || typeof WebSocket === 'undefined') return;
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host || 'localhost:8000';
      this.socket = new WebSocket(`${proto}//${host}/ws/session/${sessionId}`);
      this.socket.onopen = () => { this.socketConnected = true; };
      this.socket.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'session_started') router.navigate(`#/campaigns/${msg.campaignId || this.campaignId}/sessions/${msg.sessionId || this.sessionId}`);
          else if (msg.type === 'board_move') this.tokens = this.tokens.map((t) => (t.id === msg.tokenId ? { ...t, x: msg.toX, y: msg.toY } : t));
          else if (msg.type === 'speech_action') this.events = [...this.events, { id: String(Date.now()), timestamp: new Date().toLocaleTimeString(), source: 'player', speaker: msg.speaker || 'Party Member', text: msg.transcript || '', actionType: 'speech' }];
        } catch { /* ignore */ }
      };
      this.socket.onclose = () => {
        this.socketConnected = false;
        if (router.getCurrentRoute()?.pattern.includes('/sessions/') || router.getCurrentRoute()?.pattern.includes('/lobby/')) {
          this.reconnectTimer = setTimeout(() => this.connectWebSocket(this.sessionId), 4000);
        }
      };
    } catch { this.socketConnected = false; }
  }

  public disconnectWebSocket() {
    if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
    if (this.socket) { this.socket.onclose = null; this.socket.close(); this.socket = null; }
    this.activeSocketSessionId = null;
    this.socketConnected = false;
  }

  private async loadRouteData(r: MatchedRoute) {
    const v = this.getActiveView();
    if (v === 'campaigns') this.campaigns = await appDataService.fetchCampaigns();
    else if (v === 'campaign-detail' || v === 'campaign-characters') {
      const c = r.params.campaignId || this.campaignId;
      const [camp, members, sessions, chars, rosterCamps] = await Promise.all([appDataService.fetchCampaign(c), appDataService.fetchCampaignMembers(c), appDataService.fetchCampaignSessions(c), appDataService.fetchCharacters(), appDataService.fetchRosterCampaignOptions()]);
      if (camp) { this.currentCampaign = camp; this.campaignTitle = camp.title; router.setRouteTitle('campaign:' + camp.id, camp.title); }
      this.campaignMembers = members; this.campaignSessions = sessions; this.characters = chars; this.rosterCampaigns = rosterCamps;
    } else if (v === 'characters') [this.characters, this.rosterCampaigns] = await Promise.all([appDataService.fetchCharacters(), appDataService.fetchRosterCampaignOptions()]);
    else if (v === 'character-sheet') {
      const charId = r.params.characterId || this.selectedCharacterId;
      this.selectedCharacterId = charId; this.selectedCharacter = await appDataService.fetchCharacter(charId);
      if (this.selectedCharacter?.name) { router.setRouteTitle('character:' + charId, this.selectedCharacter.name); this.breadcrumbs = router.getCurrentRoute()?.breadcrumbs || this.breadcrumbs; }
    } else if (v === 'session-lobby') {
      const cId = r.params.campaignId || this.campaignId, sId = r.params.sessionId || this.sessionId;
      const [l, chars] = await Promise.all([appDataService.fetchLobbyState(cId, sId), this.characters.length > 0 ? Promise.resolve(this.characters) : appDataService.fetchCharacters()]);
      this.lobbyParticipants = l.participants; this.lobbyAvailableCharacters = l.availableCharacters; this.characters = chars;
    } else if (v === 'session-active') {
      const cId = r.params.campaignId || this.campaignId, sId = r.params.sessionId || this.sessionId;
      const [tokens, events, chars] = await Promise.all([appDataService.fetchBoardTokens(sId), appDataService.fetchSessionEvents(sId), this.characters.length > 0 ? Promise.resolve(this.characters) : appDataService.fetchCharacters()]);
      this.tokens = tokens; this.events = events; this.characters = chars; this.resolveActiveCharacter(cId);
    }
  }

  private async handleUpdateCampaign(e: CustomEvent<UpdateCampaignPayload>) { const p = e.detail; const cId = p?.campaignId || this.campaignId; const updated = await appDataService.updateCampaign(cId, p); if (updated) { this.currentCampaign = updated; this.campaignTitle = updated.title; router.setRouteTitle('campaign:' + updated.id, updated.title); } await this.loadRouteData(this.currentRoute || router.getCurrentRoute()!); }
  private async handleCreateSession(e: CustomEvent) { const detail = e.detail || {}; const status = detail.status || 'lobby'; const newSess = await appDataService.createCampaignSession(this.campaignId, { title: detail.title || ('Session #' + ((this.campaignSessions?.length || 0) + 1)), status, scheduled_at: detail.scheduledAt || detail.scheduled_at, description: detail.description || '' }); this.campaignSessions = await appDataService.fetchCampaignSessions(this.campaignId); if (status === 'lobby') router.navigate('#/campaigns/' + this.campaignId + '/lobby/' + newSess.id); }
  private renderCampaignTabs(activeTab: 'overview' | 'characters' | 'codex' | 'analytics') { const cId = this.campaignId; return html`<nav class="campaign-nav-tabs" role="tablist" aria-label="Campaign Sections"><a class="nav-tab ${activeTab === 'overview' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'overview'} href="#/campaigns/${cId}" @click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId); }}>Overview & Sessions</a><a class="nav-tab ${activeTab === 'characters' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'characters'} href="#/campaigns/${cId}/characters" @click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId + '/characters'); }}>Party Characters</a><a class="nav-tab ${activeTab === 'codex' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'codex'} href="#/campaigns/${cId}#codex" @click=${(e: Event) => { e.preventDefault(); }}>Codex & Lore</a><a class="nav-tab ${activeTab === 'analytics' ? 'active' : ''}" role="tab" aria-selected=${activeTab === 'analytics'} href="#/campaigns/${cId}#analytics" @click=${(e: Event) => { e.preventDefault(); }}>Chronicle & Stats</a></nav>`; }
  private handleLaunchSession(e: CustomEvent) { const cId = e.detail?.campaignId || this.campaignId; const sId = e.detail?.sessionId || this.sessionId; if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify({ type: 'session_started', campaignId: cId, sessionId: sId })); router.navigate(`#/campaigns/${cId}/sessions/${sId}`); }
  public showToast(message: string, durationMs = 4000) { this.toastMessage = message; if (this.toastTimeout) clearTimeout(this.toastTimeout); this.toastTimeout = setTimeout(() => { this.toastMessage = null; this.toastTimeout = null; }, durationMs); }
  private handleSettingsClosed() { this.isSettingsOpen = false; (this.shadowRoot?.querySelector('runefoble-header')?.shadowRoot?.querySelector('#settings-trigger-btn') as HTMLElement)?.focus(); }
  private async handleCreateCharacter(e: CustomEvent<CreateCharacterPayload>) { const newChar = await appDataService.createCharacter(e.detail); this.characters = await appDataService.fetchCharacters(); if (!this.characters.some((c) => c.id === newChar.id)) this.characters = [newChar, ...this.characters]; this.showToast(`Character "${newChar.name || e.detail.name}" created successfully`); }
  private async handleAssignCampaign(e: CustomEvent<AssignCampaignEventDetail>) { const { characterId, campaignId, campaignTitle } = e.detail; await appDataService.assignCharacterCampaign(characterId, campaignId); this.characters = this.characters.map((c) => (c.id === characterId ? { ...c, campaignId, campaignTitle } : c)); this.showToast(campaignId ? `Assigned to ${campaignTitle || 'campaign'}` : 'Unassigned from campaign'); }
  private async handleDeleteCharacter(e: CustomEvent<DeleteCharacterEventDetail>) { await appDataService.deleteCharacter(e.detail.characterId); this.characters = this.characters.filter((c) => c.id !== e.detail.characterId); this.showToast('Character deleted successfully'); }
  private handleInspectCharacter(e: CustomEvent<InspectCharacterEventDetail>) { router.navigate('#/characters/' + e.detail.characterId); }
  public resolveActiveCharacter(campaignId: string): CharacterItem {
    if (this.activeCharacter) return this.activeCharacter;
    const c = this.characters.find((ch) => ch.campaignId === campaignId) || this.characters[0];
    if (c) { this.activeCharacter = c; return c; }
    const ph: CharacterItem = { id: 'char-placeholder', name: 'Adventurer', characterClass: 'Adventurer', level: 1, currentHp: 20, maxHp: 20, armorClass: 10, speed: 30, portraitUrl: '/assets/portraits/fighter.svg' };
    this.activeCharacter = ph; return ph;
  }

  private handleSelectCharacter(e: CustomEvent) {
    const detail = e.detail || {}; const charId = detail.characterId || (typeof detail === 'string' ? detail : null);
    if (!charId) return;
    const full = this.characters.find((c) => c.id === charId);
    if (full) this.activeCharacter = full;
    else if (detail.character) { const o = detail.character; this.activeCharacter = { id: o.id, name: o.name, characterClass: o.characterClass, level: o.level || 1, currentHp: 30, maxHp: 30, armorClass: 14, speed: 30, portraitUrl: o.portraitUrl || null }; }
    const sel = this.activeCharacter;
    this.lobbyParticipants = this.lobbyParticipants.map((p) => (p.userId === (detail.userId || this.currentUserId) ? { ...p, characterId: charId, characterName: sel?.name || p.characterName, characterClass: sel?.characterClass || p.characterClass, characterLevel: sel?.level || p.characterLevel, portraitUrl: sel?.portraitUrl || p.portraitUrl } : p));
  }

  private handleDmSwitchCharacter(characterId: string) { const f = this.characters.find((c) => c.id === characterId); if (f) this.activeCharacter = f; }

  render() {
    const view = this.getActiveView();
    return html`<runefoble-header data-route=${this.currentRoute?.pattern || ''} data-view=${view} data-params=${JSON.stringify(this.routeParams)} .viewMode=${this.viewMode} .isSettingsOpen=${this.isSettingsOpen} .socketConnected=${this.socketConnected} .campaignId=${this.campaignId} .sessionId=${this.sessionId} .userRole=${this.userRole} .breadcrumbs=${this.breadcrumbs} @open-settings=${() => { this.isSettingsOpen = true; }} @open-login=${() => { this.authInitialTab = 'login'; this.isAuthModalOpen = true; }} @toggle-view-mode=${(e: CustomEvent) => { this.viewMode = e.detail.viewMode; }} @campaign-changed=${(e: CustomEvent) => { this.campaignId = e.detail.campaignId; router.navigate('#/campaigns/' + e.detail.campaignId); }}></runefoble-header><main class="app-content" data-active-view=${view}>${this.renderActiveView(view)}</main>${this.toastMessage ? html`<div class="toast-notification" role="status" aria-live="polite">${this.toastMessage}</div>` : ''}<runefoble-settings-modal .open=${this.isSettingsOpen} .currentTheme=${this.currentTheme} .currentColorMode=${this.currentColorMode} @settings-closed=${this.handleSettingsClosed} @theme-changed=${(e: CustomEvent) => { if (e.detail?.theme) this.currentTheme = e.detail.theme; }} @color-mode-changed=${(e: CustomEvent) => { if (e.detail?.mode) this.currentColorMode = e.detail.mode; }}></runefoble-settings-modal><runefoble-auth-modal .open=${this.isAuthModalOpen || view === 'login'} .initialTab=${this.authInitialTab} @auth-modal-closed=${() => { this.isAuthModalOpen = false; if (this.currentRoute?.pattern === '#/login' || this.currentRoute?.pattern === '#/register') router.navigate('#/campaigns'); }}></runefoble-auth-modal>`;
  }

  private renderActiveView(v: AppActiveView) {
    if (v === 'campaigns') return html`<runefoble-campaign-dashboard .campaigns=${this.campaigns} user-id=${this.currentUserId} @select-campaign=${(e: CustomEvent) => router.navigate('#/campaigns/' + e.detail.campaignId)} @create-campaign=${async (e: CustomEvent<CreateCampaignPayload>) => { const c = await appDataService.createCampaign(e.detail); this.campaigns = await appDataService.fetchCampaigns(); router.navigate('#/campaigns/' + c.id); }}></runefoble-campaign-dashboard>`;
    if (v === 'campaign-detail' || v === 'campaign-characters') {
      const activeTab = v === 'campaign-characters' ? 'characters' : 'overview';
      return html`<div class="campaign-hub-layout"><runefoble-campaign-header .campaign=${this.currentCampaign} .canManage=${this.isDM || this.currentCampaign?.role === 'owner' || this.currentCampaign?.role === 'dm'} current-user-id=${this.currentUserId} @update-campaign=${(e: CustomEvent<UpdateCampaignPayload>) => this.handleUpdateCampaign(e)}></runefoble-campaign-header>${this.renderCampaignTabs(activeTab)}<div class="campaign-tab-content">${activeTab === 'overview' ? html`<div class="campaign-detail-layout"><runefoble-campaign-members campaign-id=${this.campaignId} campaign-title=${this.campaignTitle} .members=${this.campaignMembers} .canManage=${this.isDM} .isGm=${this.isDM} current-user-id=${this.currentUserId}></runefoble-campaign-members><runefoble-session-list campaign-id=${this.campaignId} .sessions=${this.campaignSessions} .isDm=${this.isDM} @enter-lobby=${(e: CustomEvent) => router.navigate('#/campaigns/' + this.campaignId + '/lobby/' + e.detail.sessionId)} @join-session=${(e: CustomEvent) => router.navigate('#/campaigns/' + this.campaignId + '/sessions/' + e.detail.sessionId)} @create-session=${(e: CustomEvent) => this.handleCreateSession(e)}></runefoble-session-list></div>` : html`<runefoble-character-roster campaign-id=${this.campaignId} .characters=${this.characters.filter((c) => c.campaignId === this.campaignId)} .campaigns=${this.rosterCampaigns} current-user-id=${this.currentUserId} active-filter="assigned" @create-character=${this.handleCreateCharacter} @assign-campaign=${this.handleAssignCampaign} @delete-character=${this.handleDeleteCharacter} @inspect-character=${this.handleInspectCharacter}></runefoble-character-roster>`}</div></div>`;
    }
    if (v === 'characters') return html`<runefoble-character-roster .characters=${this.characters} .campaigns=${this.rosterCampaigns} current-user-id=${this.currentUserId} @create-character=${this.handleCreateCharacter} @assign-campaign=${this.handleAssignCampaign} @delete-character=${this.handleDeleteCharacter} @inspect-character=${this.handleInspectCharacter}></runefoble-character-roster>`;
    if (v === 'character-sheet') {
      const char = this.selectedCharacter;
      const charId = this.selectedCharacterId || this.routeParams.characterId || '';
      const guardrails = char?.stand_in_guardrails;
      return html`<div class="character-sheet-view"><div class="character-sheet-header-bar"><button class="back-to-roster-btn" @click=${() => router.navigate('#/characters')}>← Back to Roster</button></div><runefoble-character-sheet .characterId=${charId} .characterName=${char?.name || 'Character Sheet'} .characterClass=${char?.characterClass || char?.character_class || 'Adventurer'} .level=${char?.level ?? 1} .currentHp=${char?.currentHp ?? char?.current_hp ?? 10} .maxHp=${char?.maxHp ?? char?.max_hp ?? 10} .armorClass=${char?.armorClass ?? char?.armor_class ?? 10} .speed=${char?.speed ?? char?.speed_ft ?? 30} .isAiStandIn=${Boolean(char?.isAiStandIn ?? char?.is_stand_in_active)} .equipment=${char?.equipment || {}} .inventory=${Array.isArray(char?.inventory) ? char.inventory : Object.values(char?.inventory || {})} .conditions=${Array.isArray(char?.conditions) ? char.conditions : Object.entries(char?.conditions || {}).map(([k, val]: [string, any]) => ({ id: k, name: val.condition || k, source: val.source || 'tactical', description: val.source || 'Tactical condition' }))} .penalties=${char?.penalties || {}} .spellSlots=${char?.spellSlots || char?.spell_slots || { 1: 4, 2: 2 }} .maxSpellSlots=${char?.maxSpellSlots || char?.max_spell_slots || char?.spell_slots || { 1: 4, 2: 2 }} .preparedSpells=${char?.preparedSpells || char?.prepared_spells || []} .spellbook=${char?.spellbook || []} @hp-change=${(e: CustomEvent) => handleSheetHpChange(this, charId, e)} @equip-item=${(e: CustomEvent) => handleSheetEquipItem(this, charId, e)} @unequip-item=${(e: CustomEvent) => handleSheetUnequipItem(this, charId, e)} @add-item=${(e: CustomEvent) => handleSheetAddItem(this, charId, e)} @remove-item=${(e: CustomEvent) => handleSheetRemoveItem(this, charId, e)} @cast-spell=${(e: CustomEvent) => handleSheetCastSpell(this, charId, e)} @prepare-spell=${(e: CustomEvent) => handleSheetPrepareSpell(this, charId, e)} @apply-condition=${(e: CustomEvent) => handleSheetApplyCondition(this, charId, e)} @remove-condition=${(e: CustomEvent) => handleSheetRemoveCondition(this, charId, e)} @expend-slot=${(e: CustomEvent) => handleSheetExpendSlot(this, charId, e)} @restore-slot=${(e: CustomEvent) => handleSheetRestoreSlot(this, charId, e)}></runefoble-character-sheet>${guardrails ? html`<runefoble-stand-in-guardrails .characterId=${charId} .characterName=${char?.name || ''} .preserveSpellSlots=${guardrails.preserve_spell_slots || {}} .protectAllies=${guardrails.protect_allies || []} .protectAllyHpThreshold=${guardrails.protect_ally_hp_threshold ?? 0.3} .riskThreshold=${guardrails.risk_threshold || 'cautious'} .avoidMelee=${guardrails.avoid_melee ?? true} .permadeathSafeguard=${guardrails.permadeath_safeguard ?? true} .customPriorities=${guardrails.custom_priorities || []}></runefoble-stand-in-guardrails>` : ''}</div>`;
    }
    if (v === 'session-lobby') return html`<runefoble-session-lobby session-id=${this.sessionId} campaign-id=${this.campaignId} session-title=${this.sessionTitle} current-user-id=${this.currentUserId} .participants=${this.lobbyParticipants} .availableCharacters=${this.lobbyAvailableCharacters} .isDm=${this.isDM} .canLaunch=${this.isDM} @select-character=${this.handleSelectCharacter} @character-selected=${this.handleSelectCharacter} @launch-session=${this.handleLaunchSession}></runefoble-session-lobby>`;
    if (v === 'profile') {
      return html`<runefoble-user-profile .user=${authService.getUser()} .currentTheme=${this.currentTheme} .currentColorMode=${this.currentColorMode} @theme-changed=${(e: CustomEvent) => { if (e.detail?.theme) this.currentTheme = e.detail.theme; }} @color-mode-changed=${(e: CustomEvent) => { if (e.detail?.mode) this.currentColorMode = e.detail.mode; }} @auth-logout=${() => { router.navigate('#/login'); }}></runefoble-user-profile>`;
    }
    if (v === 'session-active') {
      const char = this.activeCharacter || this.resolveActiveCharacter(this.campaignId);
      const isOwnerOrDm = this.isDM || this.currentCampaign?.role === 'owner' || this.currentCampaign?.role === 'dm';
      return this.viewMode === 'spectator' ? html`<runefoble-spectator-view .sessionId=${this.sessionId} .cols=${8} .rows=${8} .tokens=${this.tokens} .atmosphere=${{ location_name: 'Ancient Crypt' }} .chronicle=${this.events}></runefoble-spectator-view>` : html`<div class="layout-grid"><div class="board-column"><runefoble-plugin-slot slot-id="hud-widget" .showFallback=${false}></runefoble-plugin-slot><runefoble-board .cols=${8} .rows=${8} .tokens=${this.tokens} .fogOfWar=${true} @move-token=${(e: CustomEvent) => { if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify({ type: 'board_move', ...e.detail })); }}></runefoble-board></div><div class="character-column">${isOwnerOrDm ? html`<div class="dm-party-inspector" role="region" aria-label="DM Party Inspector"><span class="dm-badge">DM Party Inspector</span><select class="dm-character-switcher" aria-label="Switch inspected character" @change=${(e: Event) => this.handleDmSwitchCharacter((e.target as HTMLSelectElement).value)}>${this.characters.map((c) => html`<option value="${c.id}" ?selected=${c.id === char.id}>${c.name} (${c.characterClass} Lv ${c.level})</option>`)}</select></div>` : ''}<runefoble-character-card .characterName=${char.name} .characterClass=${`${char.characterClass}${char.level ? ` Lvl ${char.level}` : ''}`} .level=${char.level} .currentHp=${char.currentHp} .maxHp=${char.maxHp} .armorClass=${char.armorClass} .portraitUrl=${char.portraitUrl || ''} .isAiStandIn=${Boolean(char.isAiStandIn)}></runefoble-character-card><runefoble-plugin-slot slot-id="sidebar-tool" .showFallback=${false}></runefoble-plugin-slot><runefoble-plugin-slot slot-id="dice-panel" .showFallback=${false}></runefoble-plugin-slot></div><runefoble-watcher-feed .events=${this.events}></runefoble-watcher-feed></div><div class="voice-container"><runefoble-voice-controls .isListening=${this.isListening} @voice-toggle=${() => { this.isListening = !this.isListening; }}></runefoble-voice-controls></div>`;
    }
    return html`<div class="auth-fallback-view"><h2>Authentication Portal</h2><p>Log in or create a Runefoble adventurer account to continue.</p></div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-app': RunefobleApp;
  }
}
