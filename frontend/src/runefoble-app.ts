import { LitElement } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import './styles/themes.css';
import { appShellStyles } from './styles/app-shell.styles.ts';
import './app/component-registry.ts';
import { registerDefaultPlugins, pluginRegistry } from './components/plugins/plugin_registry.ts';
import { authService, isAuthCallbackPath } from './auth/auth-service.ts';
import { completeSignInCallback } from './app/auth-callback.ts';
import { router, registerAuthGuard, type BreadcrumbItem, type MatchedRoute, type RouteParams } from './router/index.ts';
import type { BoardToken } from '@runefoble/board-state-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';
import type { CampaignItem, CampaignMember, LobbyParticipant, LobbyCharacterOption, UpdateCampaignPayload } from '@runefoble/game-session-ui';
import type { LoreEntry } from '@runefoble/campaign-lore-ui';
import type { CharacterItem, RosterCampaignOption, CreateCharacterPayload, AssignCampaignEventDetail, DeleteCharacterEventDetail, InspectCharacterEventDetail } from '@runefoble/character-sheet-ui';
import type { CampaignSessionItem } from './components/runefoble-session-list.ts';
import type { DataFailure } from './services/data-result.ts';
import type { CampaignAnalyticsView, CampaignAtlasView } from './services/campaign-hub-client.ts';
import { handleToggleReadiness, handleToggleStandIn, handleBoardTokenAction, handleBoardAoEPlace, handleBoardSpellVFX, handleBoardConfirmGhost } from './vtt-mesh-handlers.ts';
import { loadRouteData } from './app/route-data-loader.ts';
import { renderAppShell } from './app/shell-template.ts';
import { initTheme, syncAuthState } from './app/shell-state.ts';
import { SessionSocket } from './app/session-socket.ts';
import { installTitleResolvers } from './app/title-resolver.ts';
import { updateCampaignFromEvent, createSessionFromEvent, assignRoleFromEvent, createInviteFromEvent, removeMemberFromEvent } from './app/campaign-actions.ts';
import { createCharacterFromEvent, assignCharacterFromEvent, deleteCharacterFromEvent, selectCharacterFromEvent, switchDmCharacter } from './app/character-actions.ts';

export type AppActiveView = 'login' | 'campaigns' | 'campaign-detail' | 'campaign-characters' | 'campaign-codex' | 'campaign-analytics' | 'characters' | 'character-sheet' | 'session-lobby' | 'session-active' | 'profile';

@customElement('runefoble-app')
export class RunefobleApp extends LitElement {
  static styles = [appShellStyles];

  public readonly sessionSocket = new SessionSocket(this);
  @state() public viewMode: 'party' | 'spectator' = 'party';
  @state() public isSettingsOpen = false;
  @state() public currentTheme = 'bauhaus';
  @state() public currentColorMode: 'light' | 'dark' | 'system' = 'system';
  @state() public isListening = false;
  @state() public socketConnected = false;
  @state() public campaignId = '4';
  @state() public sessionId = 'session-tomb-14';
  @state() public campaignTitle = '';
  @state() public sessionTitle = '';
  @state() public loadError: DataFailure | null = null;
  @state() public selectedCharacterId = '';
  @state() public selectedCharacter: any = null;
  @state() public tokens: BoardToken[] = [];
  @state() public events: WatcherFeedEvent[] = [];
  @state() public breadcrumbs: BreadcrumbItem[] = [];
  @state() public currentRoute: MatchedRoute | null = null;
  @state() public routeParams: RouteParams = {};
  @state() public isAuthModalOpen = false;
  @state() public authError = '';
  @state() public currentUserId = '';
  @state() public userRole = 'Player';
  @state() public isDM = false;
  @state() public campaigns: CampaignItem[] = [];
  @state() public currentCampaign: CampaignItem | null = null;
  @state() public campaignMembers: CampaignMember[] = [];
  @state() public campaignSessions: CampaignSessionItem[] = [];
  @state() public campaignCodexView: 'atlas' | 'codex' = 'atlas';
  @state() public campaignAtlas: CampaignAtlasView | null = null;
  @state() public campaignLoreEntries: LoreEntry[] = [];
  @state() public campaignAnalytics: CampaignAnalyticsView | null = null;
  @state() public characters: CharacterItem[] = [];
  @state() public rosterCampaigns: RosterCampaignOption[] = [];
  @state() public lobbyParticipants: LobbyParticipant[] = [];
  @state() public lobbyAvailableCharacters: LobbyCharacterOption[] = [];
  @state() public activeCharacter: CharacterItem | null = null;
  @state() public boardCols = 10;
  @state() public boardRows = 10;
  @state() public atmosphere = { location_name: 'Sanctum of Runes' };
  @state() public toastMessage: string | null = null;
  @state() public inviteUrl = '';
  @state() public inviteToken = '';
  @state() public isAbsenteeDirectiveOpen = false;
  @state() public isAbsenteeRecapOpen = false;
  @state() public absenteeRecapData: any = null;
  private toastTimeout: ReturnType<typeof setTimeout> | null = null;
  private unlistenRouter: (() => void) | null = null;
  private unlistenAuth: (() => void) | null = null;
  private unlistenTeardown: (() => void) | null = null;
  private unlistenGuard: (() => void) | null = null;

  connectedCallback() {
    super.connectedCallback();
    initTheme(this);
    syncAuthState(this, authService.getState());
    registerDefaultPlugins(pluginRegistry, this.isDM);
    this.unlistenAuth = authService.onAuthChanged((s) => syncAuthState(this, s));
    // The router starts after the Zitadel code exchange so the guard sees the result.
    if (isAuthCallbackPath(window.location.pathname)) {
      void completeSignInCallback().then((error) => { this.authError = error; this.initRouter(); });
    } else {
      this.initRouter();
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.unlistenRouter?.();
    this.unlistenAuth?.();
    this.unlistenTeardown?.();
    this.unlistenGuard?.();
    this.sessionSocket.disconnectWebSocket();
    if (this.toastTimeout) {
      clearTimeout(this.toastTimeout);
      this.toastTimeout = null;
    }
    router.stop();
  }

  public getActiveView(): AppActiveView {
    const pat = this.currentRoute?.pattern || '';
    if (pat === '#/login' || pat === '#/register') return 'login';
    if (pat.startsWith('#/campaigns/:campaignId/lobby/')) return 'session-lobby';
    if (pat.startsWith('#/campaigns/:campaignId/sessions/')) return 'session-active';
    if (pat === '#/campaigns/:campaignId/characters') return 'campaign-characters';
    if (pat === '#/campaigns/:campaignId/codex') return 'campaign-codex';
    if (pat === '#/campaigns/:campaignId/analytics') return 'campaign-analytics';
    if (pat.startsWith('#/campaigns/:campaignId')) return 'campaign-detail';
    if (pat.startsWith('#/characters/') && pat !== '#/characters') return 'character-sheet';
    return pat === '#/characters' ? 'characters' : pat === '#/profile' ? 'profile' : 'campaigns';
  }

  private initRouter() {
    this.unlistenGuard = registerAuthGuard(router, authService);
    installTitleResolvers(this);
    this.unlistenTeardown = router.registerTeardown(() => {
      const p = router.getCurrentRoute()?.pattern || '';
      if (!p.includes('/sessions/') && !p.includes('/lobby/')) this.sessionSocket.disconnectWebSocket();
    });
    this.unlistenRouter = router.onRouteChanged((r) => this.handleRouteChanged(r));
    router.start();
    const cur = router.getCurrentRoute();
    if (cur) this.handleRouteChanged(cur);
  }

  private async handleRouteChanged(route: MatchedRoute) {
    this.currentRoute = route;
    this.routeParams = route.params;
    this.breadcrumbs = route.breadcrumbs;
    if (route.params.campaignId) {
      this.campaignId = route.params.campaignId;
      this.campaignTitle = router.resolveTitle('campaign', this.campaignId) || `Campaign #${this.campaignId}`;
    }
    if (route.params.sessionId) {
      this.sessionId = route.params.sessionId;
      this.sessionTitle = router.resolveTitle('session', this.sessionId) || router.resolveTitle('lobby', this.sessionId) || `Session #${this.sessionId}`;
    }
    if (route.params.characterId) this.selectedCharacterId = route.params.characterId;
    if (route.pattern === '#/login' || route.pattern === '#/register') {
      this.isAuthModalOpen = true;
    }
    this.sessionSocket.manageWebSocketLifecycle(route);
    await loadRouteData(this, route);
  }

  public reloadRouteData() {
    if (this.currentRoute) void loadRouteData(this, this.currentRoute);
  }

  public handleUpdateCampaign(e: CustomEvent<UpdateCampaignPayload>) { return updateCampaignFromEvent(this, e); }
  public handleCreateSession(e: CustomEvent) { return createSessionFromEvent(this, e); }
  public handleAssignRole(e: CustomEvent) { return assignRoleFromEvent(this, e); }
  public handleCreateInvite(e: CustomEvent) { return createInviteFromEvent(this, e); }
  public handleRemoveMember(e: CustomEvent) { return removeMemberFromEvent(this, e); }
  public handleCreateCharacter(e: CustomEvent<CreateCharacterPayload>) { return createCharacterFromEvent(this, e); }
  public handleAssignCampaign(e: CustomEvent<AssignCampaignEventDetail>) { return assignCharacterFromEvent(this, e); }
  public handleDeleteCharacter(e: CustomEvent<DeleteCharacterEventDetail>) { return deleteCharacterFromEvent(this, e); }
  public handleSelectCharacter(e: CustomEvent) { return selectCharacterFromEvent(this, e); }
  public handleDmSwitchCharacter(cId: string) { return switchDmCharacter(this, cId); }
  public handleInspectCharacter(e: CustomEvent<InspectCharacterEventDetail>) { router.navigate('#/characters/' + e.detail.characterId); }

  public handleLaunchSession(e: CustomEvent) {
    const cId = e.detail?.campaignId || this.campaignId;
    const sId = e.detail?.sessionId || this.sessionId;
    const socket = this.sessionSocket.current;
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'session_started', campaignId: cId, sessionId: sId }));
    router.navigate(`#/campaigns/${cId}/sessions/${sId}`);
  }

  public showToast(message: string, durationMs = 4000) {
    this.toastMessage = message;
    if (this.toastTimeout) clearTimeout(this.toastTimeout);
    this.toastTimeout = setTimeout(() => {
      this.toastMessage = null;
      this.toastTimeout = null;
    }, durationMs);
  }

  public handleSettingsClosed() {
    this.isSettingsOpen = false;
    (this.shadowRoot?.querySelector('runefoble-header')?.shadowRoot?.querySelector('#settings-trigger-btn') as HTMLElement)?.focus();
  }

  public resolveActiveCharacter(campaignId: string): CharacterItem {
    if (this.activeCharacter) return this.activeCharacter;
    const c = this.characters.find((ch) => ch.campaignId === campaignId) || this.characters[0] || { id: 'char-placeholder', name: 'Adventurer', characterClass: 'Adventurer', level: 1, currentHp: 20, maxHp: 20, armorClass: 10, speed: 30, portraitUrl: '/assets/portraits/fighter.svg' };
    this.activeCharacter = c;
    return c;
  }

  /** Board stream URL. Moves are sent here as the confirm_move action (TASK-0563). */
  public getWebSocketUrl(): string {
    if (typeof window === 'undefined') return '';
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host || 'localhost:8000'}/ws/boards/${this.sessionId}`;
  }

  public handleToggleReadiness(e: CustomEvent) { handleToggleReadiness(this, e, this.sessionSocket.current); }

  public handleToggleStandIn(e: CustomEvent) {
    handleToggleStandIn(this, e, this.sessionSocket.current);
    const { isAbsent } = e.detail || {};
    if (isAbsent) {
      this.isAbsenteeDirectiveOpen = true;
      this.showToast('Stand-In Activated: Directives drawer opened');
    } else {
      this.triggerAbsenteeRecap(this.activeCharacter?.id || this.selectedCharacterId);
    }
  }

  public handleBoardTokenAction(e: CustomEvent) { handleBoardTokenAction(e, this.sessionSocket.current); }
  public handleBoardAoEPlace(e: CustomEvent) { handleBoardAoEPlace(e, this.sessionSocket.current); }
  public handleBoardSpellVFX(e: CustomEvent) { handleBoardSpellVFX(e, this.sessionSocket.current); }
  public handleBoardConfirmGhost(e: CustomEvent) { handleBoardConfirmGhost(e, this.sessionSocket.current); }

  public triggerAbsenteeRecap(characterId?: string) {
    const c = this.characters.find((ch) => ch.id === characterId) || this.activeCharacter || this.selectedCharacter;
    this.absenteeRecapData = {
      characterName: c?.name || 'Valeros of Korvosa',
      persona: 'The Cautious Defender',
      penalties: ['drunk', 'foolishness'],
      narrative: 'While you were absent, The Watcher guided your hero with penalties.',
      highlights: ['Parried a critical strike', 'Tasted dwarven ale'],
      hpDelta: -4,
      itemsAcquired: ['Mysterious Relic', '25 Gold Pieces'],
    };
    this.isAbsenteeRecapOpen = true;
  }

  render() {
    return renderAppShell(this);
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-app': RunefobleApp;
  }
}
