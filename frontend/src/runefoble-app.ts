import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import './styles/themes.css';
import { appShellStyles } from './styles/app-shell.styles.ts';
import './components/runefoble-header.ts';
import './components/runefoble-settings-modal.ts';
import '@runefoble/board-state-ui';
import '@runefoble/character-sheet-ui';
import '@runefoble/game-session-ui';
import '@runefoble/the-watcher-ui';
import '@runefoble/voice-agent-ui';
import type { BoardToken } from '@runefoble/board-state-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';

const DEFAULT_TOKENS: BoardToken[] = [
  { id: '1', name: 'Valeros', x: 2, y: 3, color: 'var(--rf-accent-secondary)', hp: 38, maxHp: 45, visionRadius: 2 },
  { id: '2', name: 'Kyra (AI)', x: 3, y: 3, isAiControlled: true, color: 'var(--rf-accent-primary)', hp: 28, maxHp: 32, visionRadius: 2 },
  { id: '3', name: 'Goblin Scout', x: 5, y: 1, isHostile: true, color: 'var(--rf-accent-tertiary)', hp: 7, maxHp: 12 },
  { id: '4', name: 'Red Dragon Wyrmling', x: 6, y: 5, isHostile: true, color: 'var(--rf-border-color)', hp: 52, maxHp: 75 },
];

const DEFAULT_EVENTS: WatcherFeedEvent[] = [
  { id: '1', timestamp: '19:45:00', source: 'watcher_dm', speaker: 'The Watcher (AI DM)', text: 'Welcome back, adventurers.', actionType: 'dm_ruling' },
  { id: '2', timestamp: '19:45:20', source: 'player', speaker: 'Valeros', text: '"I ready my shield and move two steps forward."', actionType: 'speech' },
  { id: '3', timestamp: '19:45:30', source: 'stand_in', speaker: 'Kyra (AI Stand-in, Drunk)', text: '"Hah! No dragon can outwit Sarenrae finest vintner!"', actionType: 'speech' },
];

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
  @state() private tokens: BoardToken[] = DEFAULT_TOKENS;
  @state() private events: WatcherFeedEvent[] = DEFAULT_EVENTS;

  private socket: WebSocket | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.initThemeAndColorMode();
    this.initWebSocket();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.socket) this.socket.close();
  }

  private initThemeAndColorMode() {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const storedTheme = window.localStorage.getItem('runefoble-theme');
        if (storedTheme) this.currentTheme = storedTheme;
        const storedMode = window.localStorage.getItem('runefoble-color-mode');
        if (storedMode && ['light', 'dark', 'system'].includes(storedMode)) {
          this.currentColorMode = storedMode as 'light' | 'dark' | 'system';
        }
      }
    } catch { /* Storage access restricted */ }
    if (typeof document !== 'undefined' && document.documentElement) {
      document.documentElement.setAttribute('data-theme', this.currentTheme);
      document.documentElement.setAttribute('data-color-mode', this.currentColorMode);
    }
  }

  private initWebSocket() {
    try {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host || 'localhost:8000';
      this.socket = new WebSocket(`${proto}//${host}/ws/session/${this.sessionId}`);
      this.socket.onopen = () => { this.socketConnected = true; };
      this.socket.onmessage = (event) => {
        try { this.handleIncomingSocketMessage(JSON.parse(event.data)); } catch { /* ignore */ }
      };
      this.socket.onclose = () => { this.socketConnected = false; setTimeout(() => this.initWebSocket(), 4000); };
      this.socket.onerror = () => { this.socketConnected = false; };
    } catch { this.socketConnected = false; }
  }

  private handleIncomingSocketMessage(msg: Record<string, any>) {
    if (msg.type === 'board_move') {
      const { tokenId, toX, toY } = msg;
      this.tokens = this.tokens.map((t) => (t.id === tokenId ? { ...t, x: toX, y: toY } : t));
      const tokenName = this.tokens.find((t) => t.id === tokenId)?.name || 'Token';
      this.events = [...this.events, { id: String(Date.now()), timestamp: new Date().toLocaleTimeString(), source: 'system', speaker: 'The Watcher', text: `${tokenName} moved to (${toX}, ${toY}).`, actionType: 'board_move' }];
    } else if (msg.type === 'speech_action') {
      this.events = [...this.events, { id: String(Date.now()), timestamp: new Date().toLocaleTimeString(), source: 'player', speaker: msg.speaker || 'Party Member', text: msg.transcript || '', actionType: 'speech' }];
    }
  }

  private handleMoveToken(e: CustomEvent) {
    const { tokenId, toX, toY } = e.detail;
    this.tokens = this.tokens.map((t) => (t.id === tokenId ? { ...t, x: toX, y: toY } : t));
    const tokenName = this.tokens.find((t) => t.id === tokenId)?.name || 'Token';
    this.events = [...this.events, { id: String(Date.now()), timestamp: new Date().toLocaleTimeString(), source: 'system', speaker: 'The Watcher', text: `${tokenName} moved to (${toX}, ${toY}).`, actionType: 'board_move' }];
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: 'board_move', tokenId, toX, toY }));
    }
  }

  private toggleListening() {
    this.isListening = !this.isListening;
    if (this.isListening) {
      const speech = '"Speak and the board obeys! Moving to engage the Goblin Scout."';
      this.events = [...this.events, { id: String(Date.now()), timestamp: new Date().toLocaleTimeString(), source: 'player', speaker: 'You (Voice Input)', text: speech, actionType: 'speech' }];
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: 'speech_action', speaker: 'You (Voice Input)', transcript: speech }));
      }
    }
  }

  private handleSettingsClosed() {
    this.isSettingsOpen = false;
    const trigger = this.shadowRoot?.querySelector('runefoble-header')?.shadowRoot?.querySelector('#settings-trigger-btn') as HTMLElement;
    trigger?.focus();
  }

  render() {
    return html`
      <runefoble-header
        .viewMode=${this.viewMode} .isSettingsOpen=${this.isSettingsOpen}
        .socketConnected=${this.socketConnected} .campaignId=${this.campaignId} .sessionId=${'14'}
        @open-settings=${() => { this.isSettingsOpen = true; }}
        @toggle-view-mode=${(e: CustomEvent) => { this.viewMode = e.detail.viewMode; }}
        @campaign-changed=${(e: CustomEvent) => { this.campaignId = e.detail.campaignId; }}
      ></runefoble-header>
      ${this.viewMode === 'spectator' ? html`
        <runefoble-spectator-view
          sessionId="14" .cols=${8} .rows=${8}
          .tokens=${this.tokens.map((t) => ({ id: t.id, name: t.name, x: t.x, y: t.y, color: t.color, isAiControlled: t.isAiControlled }))}
          .atmosphere=${{ location_name: 'Ancient Crypt', lighting: 'Torches', mood: 'Suspenseful', description: 'Ancient shadows crawl.', ambient_audio_prompt: 'water' }}
          .chronicle=${this.events.map((e) => ({ id: e.id, speaker: e.speaker, text: e.text, timestamp: e.timestamp, action_type: e.actionType }))}
          .round=${3}
        ></runefoble-spectator-view>
      ` : html`
        <div class="layout-grid">
          <runefoble-board
            .cols=${8} .rows=${8} .tokens=${this.tokens} .fogOfWar=${true}
            watcherStatus="${this.isListening ? 'Streaming voice & resolving actions...' : 'Observing session. Speak to command.'}"
            @move-token=${this.handleMoveToken}
          ></runefoble-board>
          <div class="character-column">
            <runefoble-character-card
              characterName="Kyra the Sun Maiden" characterClass="Cleric Lvl 4"
              .isAiStandIn=${true} .currentHp=${28} .maxHp=${32} .armorClass=${16} .initiative=${0} .speed=${25}
              .conditions=${[
                { id: 'pen-1', name: 'Drunk (Missed Session)', severity: 'moderate', source: 'session_penalty', description: 'Player missed session! DM penalty applied: +2 bravery, -2 perception.' },
                { id: 'pen-2', name: 'Foolishness', severity: 'minor', source: 'session_penalty', description: 'AI will roleplay boldly without second-guessing danger.' },
              ]}
            ></runefoble-character-card>
            <runefoble-dice-roller sessionId="14" rollerId="char-kyra" rollerName="Kyra the Sun Maiden" formula="1d20+4"></runefoble-dice-roller>
          </div>
          <runefoble-watcher-feed .events=${this.events}></runefoble-watcher-feed>
        </div>
        <div class="voice-container">
          <runefoble-voice-controls .isListening=${this.isListening} @voice-toggle=${this.toggleListening}></runefoble-voice-controls>
        </div>
      `}
      <runefoble-settings-modal
        .open=${this.isSettingsOpen} .currentTheme=${this.currentTheme} .currentColorMode=${this.currentColorMode}
        @settings-closed=${this.handleSettingsClosed}
        @theme-changed=${(e: CustomEvent) => { if (e.detail?.theme) this.currentTheme = e.detail.theme; }}
        @color-mode-changed=${(e: CustomEvent) => { if (e.detail?.mode) this.currentColorMode = e.detail.mode; }}
      ></runefoble-settings-modal>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-app': RunefobleApp;
  }
}
