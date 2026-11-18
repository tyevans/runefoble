import { LitElement } from 'lit';
import { wsUrl } from '@runefoble/ui-core';
import { customElement, state } from 'lit/decorators.js';
import './styles/themes.css';
import { appShellStyles } from './styles/app-shell.styles.ts';
import { loadViewBundles } from './app/component-registry.ts';
import { authService, isAuthCallbackPath } from './auth/auth-service.ts';
import { AuthContextProviderController } from './auth/auth-context-provider.ts';
import { completeSignInCallback } from './app/auth-callback.ts';
import { router, registerAuthGuard, type BreadcrumbItem, type MatchedRoute, type RouteParams } from './router/index.ts';
import { resolveActiveView, type AppActiveView } from './router/view-resolver.ts';
import type { BoardToken } from '@runefoble/board-state-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';
import type {
  CampaignItem,
  CampaignMember,
  CaravanContractItem,
  LobbyParticipant,
  LobbyCharacterOption,
} from '@runefoble/game-session-ui';
import type { LoreEntry } from '@runefoble/campaign-lore-ui';
import type {
  CharacterItem,
  RosterCampaignOption,
} from '@runefoble/character-sheet-ui';
import type { CampaignSessionItem } from './components/runefoble-session-list.ts';
import type { DataFailure } from './services/data-result.ts';
import type { CampaignAnalyticsView, CampaignAtlasView } from './services/campaign-hub-client.ts';
import type { CampaignCapabilities } from './services/campaign-capabilities.ts';
import { loadRouteData } from './app/data-loader.ts';
import { applyRouteState } from './app/route-state.ts';
import { renderAppShell } from './app/shell-template.ts';
import { initTheme, syncAuthState } from './app/shell-state.ts';
import { SessionSocket } from './app/session-socket.ts';
import { installTitleResolvers } from './app/title-resolver.ts';
import { pickActiveCharacter } from './app/active-character.ts';
import type { BoardTarget } from './app/board-dm-controls.ts';

@customElement('runefoble-app')
export class RunefobleApp extends LitElement {
  static styles = [appShellStyles];

  public readonly sessionSocket = new SessionSocket(this);
  public readonly authContextProvider = new AuthContextProviderController(this, authService);
  @state() public viewMode: 'party' | 'spectator' = 'party';
  @state() public isSettingsOpen = false;
  @state() public currentTheme = 'bauhaus';
  @state() public currentColorMode: 'light' | 'dark' | 'system' = 'system';
  @state() public isListening = false;
  @state() public socketConnected = false;
  @state() public campaignId = '';
  @state() public sessionId = '';
  @state() public campaignTitle = '';
  @state() public sessionTitle = '';
  @state() public loadError: DataFailure | null = null;
  @state() public selectedCharacterId = '';
  @state() public selectedCharacter: any = null;
  @state() public tokens: BoardToken[] = [];
  @state() public events: WatcherFeedEvent[] = [];
  @state() public breadcrumbs: BreadcrumbItem[] = [];
  @state() public currentRoute: MatchedRoute | null = null;
  @state() public caravanContracts: CaravanContractItem[] = [];
  @state() public routeParams: RouteParams = {};
  @state() public isAuthModalOpen = false;
  @state() public authError = '';
  @state() public currentUserId = '';
  @state() public userRole = 'Player';
  @state() public campaigns: CampaignItem[] = [];
  @state() public currentCampaign: CampaignItem | null = null;
  @state() public campaignCapabilities: CampaignCapabilities | null = null;
  @state() public campaignMembers: CampaignMember[] = [];
  @state() public campaignSessions: CampaignSessionItem[] = [];
  @state() public campaignCodexView: 'atlas' | 'codex' = 'atlas';
  @state() public campaignAtlas: CampaignAtlasView | null = null;
  @state() public campaignPinError: string | null = null;
  @state() public campaignEntryError: string | null = null;
  @state() public campaignLoreEntries: LoreEntry[] = [];
  @state() public campaignAnalytics: CampaignAnalyticsView | null = null;
  @state() public characters: CharacterItem[] = [];
  @state() public rosterCampaigns: RosterCampaignOption[] = [];
  @state() public lobbyParticipants: LobbyParticipant[] = [];
  @state() public lobbyAvailableCharacters: LobbyCharacterOption[] = [];
  @state() public activeCharacter: CharacterItem | null = null;
  @state() public boardCols = 10;
  @state() public boardRows = 10;
  @state() public atmosphere: { location_name: string } = { location_name: '' };
  @state() public toastMessage: string | null = null;
  @state() public inviteUrl = '';
  @state() public inviteToken = '';
  @state() public isAbsenteeDirectiveOpen = false;
  @state() public boardTarget: BoardTarget | null = null;
  @state() public isMapSwitcherOpen = false;
  private toastTimeout: ReturnType<typeof setTimeout> | null = null;
  private unlistenRouter: (() => void) | null = null;
  private unlistenAuth: (() => void) | null = null;
  private unlistenTeardown: (() => void) | null = null;
  private unlistenGuard: (() => void) | null = null;

  connectedCallback() {
    super.connectedCallback();
    initTheme(this);
    syncAuthState(this, authService.getState());
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
    return resolveActiveView(this.currentRoute);
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
    applyRouteState(this, route);
    this.sessionSocket.manageWebSocketLifecycle(route);
    loadViewBundles(this.getActiveView()).catch((error) => {
      console.error('A view bundle failed to load.', error);
      this.showToast('Part of this view failed to load. Reload the page to retry.');
    });
    await loadRouteData(this, route);
  }

  public reloadRouteData() {
    if (this.currentRoute) void loadRouteData(this, this.currentRoute);
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

  /** The bound character, or null when the roster is empty. Never a placeholder. */
  public resolveActiveCharacter(campaignId: string): CharacterItem | null {
    if (this.activeCharacter) return this.activeCharacter;
    this.activeCharacter = pickActiveCharacter(this.characters, campaignId);
    return this.activeCharacter;
  }

  /** Board stream URL. Moves are sent here as the confirm_move action (TASK-0563). */
  public getWebSocketUrl(): string {
    if (typeof window === 'undefined') return '';
    return wsUrl(`/ws/boards/${this.sessionId}`);
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
