import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import './styles/themes.css';
import { appShellStyles } from './styles/app-shell.styles.ts';
import './components/runefoble-header.ts';
import './components/runefoble-settings-modal.ts';
import './components/runefoble-auth-modal.ts';
import './components/runefoble-session-list.ts';
import '@runefoble/board-state-ui';
import '@runefoble/character-sheet-ui';
import '@runefoble/game-session-ui';
import '@runefoble/the-watcher-ui';
import '@runefoble/voice-agent-ui';
import type { BoardToken } from '@runefoble/board-state-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';
import type { CampaignItem, CampaignMember, CreateCampaignPayload, LobbyParticipant, LobbyCharacterOption } from '@runefoble/game-session-ui';
import type { CharacterItem, RosterCampaignOption } from '@runefoble/character-sheet-ui';
import type { CampaignSessionItem } from './components/runefoble-session-list.ts';
import { router, type BreadcrumbItem, type MatchedRoute, type RouteParams } from './router/router.ts';
import { authService, type AuthState } from './auth/auth-service.ts';
import { appDataService } from './services/app-data-service.ts';

export type AppActiveView = 'login' | 'campaigns' | 'campaign-detail' | 'characters' | 'session-lobby' | 'session-active';

@customElement('runefoble-app')
export class RunefobleApp extends LitElement {
  static styles = [appShellStyles];

  @state() private viewMode: 'party' | 'spectator' = 'party';
  @state() private isSettingsOpen = false;
  @state() private currentTheme = 'bauhaus';
  @state() private currentColorMode: 'light' | 'dark' | 'system' = 'system';
  @state() private isListening = false;
  @state() private socketConnected = false;
  @state() private campaignId = '4';
  @state() private sessionId = 'session-tomb-14';
  @state() private campaignTitle = 'Tomb of the Star-Eater';
  @state() private sessionTitle = 'Session #14';
  @state() private tokens: BoardToken[] = [];
  @state() private events: WatcherFeedEvent[] = [];
  @state() private breadcrumbs: BreadcrumbItem[] = [];
  @state() private currentRoute: MatchedRoute | null = null;
  @state() public routeParams: RouteParams = {};
  @state() private isAuthModalOpen = false;
  @state() private authInitialTab: 'login' | 'register' = 'login';
  @state() private currentUserId = 'user-valeros';
  @state() private userRole = 'Player';
  @state() private isDM = false;

  @state() private campaigns: CampaignItem[] = [];
  @state() private campaignMembers: CampaignMember[] = [];
  @state() private campaignSessions: CampaignSessionItem[] = [];
  @state() private characters: CharacterItem[] = [];
  @state() private rosterCampaigns: RosterCampaignOption[] = [];
  @state() private lobbyParticipants: LobbyParticipant[] = [];
  @state() private lobbyAvailableCharacters: LobbyCharacterOption[] = [];

  private socket: WebSocket | null = null;
  private activeSocketSessionId: string | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private unlistenRouter: (() => void) | null = null;
  private unlistenAuth: (() => void) | null = null;
  private unlistenTeardown: (() => void) | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.initTheme();
    this.syncAuthState(authService.getState());
    this.unlistenAuth = authService.onAuthChanged((s) => this.syncAuthState(s));
    this.initRouter();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.unlistenRouter?.(); this.unlistenAuth?.(); this.unlistenTeardown?.();
    this.disconnectWebSocket();
    router.stop();
  }

  public getActiveView(): AppActiveView {
    const pat = this.currentRoute?.pattern || '';
    if (pat === '#/login' || pat === '#/register') return 'login';
    if (pat.startsWith('#/campaigns/:campaignId/lobby/')) return 'session-lobby';
    if (pat.startsWith('#/campaigns/:campaignId/sessions/')) return 'session-active';
    if (pat.startsWith('#/campaigns/:campaignId')) return 'campaign-detail';
    if (pat === '#/characters') return 'characters';
    return 'campaigns';
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
    document?.documentElement?.setAttribute('data-theme', this.currentTheme);
    document?.documentElement?.setAttribute('data-color-mode', this.currentColorMode);
  }

  private initRouter() {
    router.setTitleResolver((type, id) => {
      if (type === 'campaign' && id === '4') return 'Tomb of the Star-Eater';
      if (type === 'campaign' && id === '5') return 'Whispering Depths';
      return (type === 'session' && (id === '14' || id === 'session-tomb-14')) ? 'Session #14' : type === 'lobby' ? `Lobby ${id}` : undefined;
    });
    this.unlistenTeardown = router.registerTeardown(() => {
      const p = router.getCurrentRoute()?.pattern || '';
      if (!p.includes('/sessions/') && !p.includes('/lobby/')) this.disconnectWebSocket();
    });
    this.unlistenRouter = router.onRouteChanged((r) => this.handleRouteChanged(r));
    router.start();
    const cur = router.getCurrentRoute();
    if (cur) this.handleRouteChanged(cur);
  }

  private async handleRouteChanged(route: MatchedRoute) {
    this.currentRoute = route; this.routeParams = route.params; this.breadcrumbs = route.breadcrumbs;
    if (route.params.campaignId) {
      this.campaignId = route.params.campaignId;
      this.campaignTitle = router.resolveTitle('campaign', this.campaignId) || `Campaign #${this.campaignId}`;
    }
    if (route.params.sessionId) {
      this.sessionId = route.params.sessionId;
      this.sessionTitle = router.resolveTitle('session', this.sessionId) || router.resolveTitle('lobby', this.sessionId) || `Session #${this.sessionId}`;
    }
    if (route.pattern === '#/login' || route.pattern === '#/register') {
      this.authInitialTab = route.pattern === '#/register' ? 'register' : 'login';
      this.isAuthModalOpen = true;
    }
    this.manageWebSocketLifecycle(route);
    await this.loadRouteData(route);
  }

  private manageWebSocketLifecycle(route: MatchedRoute) {
    const isSession = route.pattern.includes('/sessions/') || route.pattern.includes('/lobby/');
    if (isSession) {
      const target = route.params.sessionId || this.sessionId;
      if (!this.socket || this.activeSocketSessionId !== target) this.connectWebSocket(target);
    } else {
      this.disconnectWebSocket();
    }
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
    else if (v === 'campaign-detail') {
      const c = r.params.campaignId || this.campaignId;
      [this.campaignMembers, this.campaignSessions] = await Promise.all([appDataService.fetchCampaignMembers(c), appDataService.fetchCampaignSessions(c)]);
    } else if (v === 'characters') {
      [this.characters, this.rosterCampaigns] = await Promise.all([appDataService.fetchCharacters(), appDataService.fetchRosterCampaignOptions()]);
    } else if (v === 'session-lobby') {
      const l = await appDataService.fetchLobbyState(r.params.sessionId || this.sessionId);
      this.lobbyParticipants = l.participants;
      this.lobbyAvailableCharacters = l.availableCharacters;
    } else if (v === 'session-active') {
      const s = r.params.sessionId || this.sessionId;
      [this.tokens, this.events] = await Promise.all([appDataService.fetchBoardTokens(s), appDataService.fetchSessionEvents(s)]);
    }
  }

  private handleLaunchSession(e: CustomEvent) {
    const cId = e.detail?.campaignId || this.campaignId;
    const sId = e.detail?.sessionId || this.sessionId;
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify({ type: 'session_started', campaignId: cId, sessionId: sId }));
    router.navigate(`#/campaigns/${cId}/sessions/${sId}`);
  }

  private handleSettingsClosed() {
    this.isSettingsOpen = false;
    (this.shadowRoot?.querySelector('runefoble-header')?.shadowRoot?.querySelector('#settings-trigger-btn') as HTMLElement)?.focus();
  }

  render() {
    const view = this.getActiveView();
    return html`
      <runefoble-header data-route=${this.currentRoute?.pattern || ''} data-view=${view} data-params=${JSON.stringify(this.routeParams)} .viewMode=${this.viewMode} .isSettingsOpen=${this.isSettingsOpen} .socketConnected=${this.socketConnected} .campaignId=${this.campaignId} .sessionId=${this.sessionId} .userRole=${this.userRole} .breadcrumbs=${this.breadcrumbs} @open-settings=${() => { this.isSettingsOpen = true; }} @open-login=${() => { this.authInitialTab = 'login'; this.isAuthModalOpen = true; }} @toggle-view-mode=${(e: CustomEvent) => { this.viewMode = e.detail.viewMode; }} @campaign-changed=${(e: CustomEvent) => { this.campaignId = e.detail.campaignId; router.navigate('#/campaigns/' + e.detail.campaignId); }}></runefoble-header>
      <main class="app-content" data-active-view=${view}>${this.renderActiveView(view)}</main>
      <runefoble-settings-modal .open=${this.isSettingsOpen} .currentTheme=${this.currentTheme} .currentColorMode=${this.currentColorMode} @settings-closed=${this.handleSettingsClosed} @theme-changed=${(e: CustomEvent) => { if (e.detail?.theme) this.currentTheme = e.detail.theme; }} @color-mode-changed=${(e: CustomEvent) => { if (e.detail?.mode) this.currentColorMode = e.detail.mode; }}></runefoble-settings-modal>
      <runefoble-auth-modal .open=${this.isAuthModalOpen || view === 'login'} .initialTab=${this.authInitialTab} @auth-modal-closed=${() => { this.isAuthModalOpen = false; if (this.currentRoute?.pattern === '#/login' || this.currentRoute?.pattern === '#/register') router.navigate('#/campaigns'); }}></runefoble-auth-modal>
    `;
  }

  private renderActiveView(v: AppActiveView) {
    if (v === 'campaigns') return html`<runefoble-campaign-dashboard .campaigns=${this.campaigns} user-id=${this.currentUserId} @select-campaign=${(e: CustomEvent) => router.navigate('#/campaigns/' + e.detail.campaignId)} @create-campaign=${async (e: CustomEvent<CreateCampaignPayload>) => { const c = await appDataService.createCampaign(e.detail); this.campaigns = await appDataService.fetchCampaigns(); router.navigate('#/campaigns/' + c.id); }}></runefoble-campaign-dashboard>`;
    if (v === 'campaign-detail') return html`<div class="campaign-detail-layout"><runefoble-campaign-members campaign-id=${this.campaignId} campaign-title=${this.campaignTitle} .members=${this.campaignMembers} .canManage=${this.isDM} .isGm=${this.isDM} current-user-id=${this.currentUserId}></runefoble-campaign-members><runefoble-session-list campaign-id=${this.campaignId} .sessions=${this.campaignSessions} .isDm=${this.isDM} @enter-lobby=${(e: CustomEvent) => router.navigate('#/campaigns/' + this.campaignId + '/lobby/' + e.detail.sessionId)} @join-session=${(e: CustomEvent) => router.navigate('#/campaigns/' + this.campaignId + '/sessions/' + e.detail.sessionId)} @create-session=${() => router.navigate('#/campaigns/' + this.campaignId + '/lobby/new')}></runefoble-session-list></div>`;
    if (v === 'characters') return html`<runefoble-character-roster .characters=${this.characters} .campaigns=${this.rosterCampaigns} current-user-id=${this.currentUserId}></runefoble-character-roster>`;
    if (v === 'session-lobby') return html`<runefoble-session-lobby session-id=${this.sessionId} campaign-id=${this.campaignId} session-title=${this.sessionTitle} current-user-id=${this.currentUserId} .participants=${this.lobbyParticipants} .availableCharacters=${this.lobbyAvailableCharacters} .isDm=${this.isDM} .canLaunch=${this.isDM} @launch-session=${this.handleLaunchSession}></runefoble-session-lobby>`;
    if (v === 'session-active') {
      return this.viewMode === 'spectator' ? html`<runefoble-spectator-view .sessionId=${this.sessionId} .cols=${8} .rows=${8} .tokens=${this.tokens} .atmosphere=${{ location_name: 'Ancient Crypt' }} .chronicle=${this.events}></runefoble-spectator-view>` : html`
        <div class="layout-grid">
          <runefoble-board .cols=${8} .rows=${8} .tokens=${this.tokens} .fogOfWar=${true} @move-token=${(e: CustomEvent) => { if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify({ type: 'board_move', ...e.detail })); }}></runefoble-board>
          <div class="character-column"><runefoble-character-card characterName="Kyra the Sun Maiden" characterClass="Cleric Lvl 4" .isAiStandIn=${true} .currentHp=${28} .maxHp=${32}></runefoble-character-card></div>
          <runefoble-watcher-feed .events=${this.events}></runefoble-watcher-feed>
        </div>
        <div class="voice-container"><runefoble-voice-controls .isListening=${this.isListening} @voice-toggle=${() => { this.isListening = !this.isListening; }}></runefoble-voice-controls></div>
      `;
    }
    return html`<div class="auth-fallback-view"><h2>Authentication Portal</h2><p>Log in or create a Runefoble adventurer account to continue.</p></div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-app': RunefobleApp;
  }
}
