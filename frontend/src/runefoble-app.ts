import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import './styles/themes.css';
import './components/runefoble-theme-switcher.ts';
import '@runefoble/board-state-ui';
import '@runefoble/character-sheet-ui';
import '@runefoble/game-session-ui';
import '@runefoble/the-watcher-ui';
import '@runefoble/voice-agent-ui';
import type { BoardToken } from '@runefoble/board-state-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';

@customElement('runefoble-app')
export class RunefobleApp extends LitElement {
  @state() private viewMode: 'party' | 'spectator' = 'party';
  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background-color: var(--rf-bg-canvas, #f8f9fa);
      color: var(--rf-text-primary, #121212);
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      padding: 24px;
      box-sizing: border-box;
      transition: background-color 0.2s ease, color 0.2s ease;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 16px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand h1 {
      font-size: 1.9rem;
      margin: 0;
      color: var(--rf-text-primary, #121212);
      font-weight: 900;
      letter-spacing: -0.5px;
    }
    .tagline {
      font-size: 0.9rem;
      color: var(--rf-text-muted, #4b5563);
    }
    .header-actions {
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }
    .session-info {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 0.85rem;
    }
    .badge-live {
      background: var(--rf-bg-surface, #ffffff);
      color: var(--rf-accent-primary, #e63946);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      padding: 4px 12px;
      font-weight: 700;
    }
    .badge-socket {
      font-size: 0.75rem;
      padding: 4px 10px;
      border-radius: var(--rf-border-radius, 0px);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      background: var(--rf-bg-surface, #ffffff);
      font-weight: 700;
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    }
    .badge-socket.connected {
      color: var(--rf-color-blue, #1d3557);
    }
    .badge-socket.disconnected {
      color: var(--rf-color-red, #e63946);
    }
    .layout-grid {
      display: grid;
      grid-template-columns: 1fr 340px 420px;
      gap: 24px;
      align-items: start;
    }
    @media (max-width: 1280px) {
      .layout-grid {
        grid-template-columns: 1fr;
      }
    }
  `;

  @state() private isListening = false;
  @state() private socketConnected = false;
  @state() private tokens: BoardToken[] = [
    { id: '1', name: 'Valeros', x: 2, y: 3, color: '#1d3557', hp: 38, maxHp: 45, visionRadius: 2 },
    { id: '2', name: 'Kyra (AI)', x: 3, y: 3, isAiControlled: true, color: '#e63946', hp: 28, maxHp: 32, visionRadius: 2 },
    { id: '3', name: 'Goblin Scout', x: 5, y: 1, isHostile: true, color: '#ffb703', hp: 7, maxHp: 12 },
    { id: '4', name: 'Red Dragon Wyrmling', x: 6, y: 5, isHostile: true, color: '#121212', hp: 52, maxHp: 75 },
  ];

  @state() private events: WatcherFeedEvent[] = [
    {
      id: '1',
      timestamp: '19:45:00',
      source: 'watcher_dm',
      speaker: 'The Watcher (AI DM)',
      text: 'Welcome back, adventurers. The gloom of the Whispering Crypt hangs thick. Ahead, two glowing eyes appear in the corridor.',
      actionType: 'dm_ruling',
    },
    {
      id: '2',
      timestamp: '19:45:20',
      source: 'player',
      speaker: 'Valeros (Player Voice)',
      text: '"I ready my shield and move two steps forward to protect Kyra."',
      actionType: 'speech',
    },
    {
      id: '3',
      timestamp: '19:45:30',
      source: 'stand_in',
      speaker: 'Kyra (AI Stand-in, Drunk)',
      text: '"Hah! No dragon can outwit Sarenrae\'s finest vintner! *stumbles forward*"',
      actionType: 'speech',
    },
  ];

  private socket: WebSocket | null = null;
  private sessionId = 'session-tomb-14';

  connectedCallback() {
    super.connectedCallback();
    this.initWebSocket();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.socket) {
      this.socket.close();
    }
  }

  private initWebSocket() {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host || 'localhost:8000';
      const wsUrl = `${protocol}//${host}/ws/session/${this.sessionId}`;

      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        this.socketConnected = true;
      };

      this.socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleIncomingSocketMessage(msg);
        } catch {
          // Ignore invalid frames
        }
      };

      this.socket.onclose = () => {
        this.socketConnected = false;
        setTimeout(() => this.initWebSocket(), 4000);
      };

      this.socket.onerror = () => {
        this.socketConnected = false;
      };
    } catch {
      this.socketConnected = false;
    }
  }

  private handleIncomingSocketMessage(msg: Record<string, any>) {
    if (msg.type === 'board_move') {
      const { tokenId, toX, toY } = msg;
      this.tokens = this.tokens.map((t) => (t.id === tokenId ? { ...t, x: toX, y: toY } : t));
      const tokenName = this.tokens.find((t) => t.id === tokenId)?.name || 'Token';
      this.events = [
        ...this.events,
        {
          id: String(Date.now()),
          timestamp: new Date().toLocaleTimeString(),
          source: 'system',
          speaker: 'The Watcher',
          text: `${tokenName} moved to (${toX}, ${toY}).`,
          actionType: 'board_move',
        },
      ];
    } else if (msg.type === 'speech_action') {
      this.events = [
        ...this.events,
        {
          id: String(Date.now()),
          timestamp: new Date().toLocaleTimeString(),
          source: 'player',
          speaker: msg.speaker || 'Party Member',
          text: msg.transcript || '',
          actionType: 'speech',
        },
      ];
    }
  }

  private toggleListening() {
    this.isListening = !this.isListening;
    if (this.isListening) {
      const speechText = '"Speak and the board obeys! Moving to engage the Goblin Scout."';
      this.events = [
        ...this.events,
        {
          id: String(Date.now()),
          timestamp: new Date().toLocaleTimeString(),
          source: 'player',
          speaker: 'You (Voice Input)',
          text: speechText,
          actionType: 'speech',
        },
      ];
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(
          JSON.stringify({
            type: 'speech_action',
            speaker: 'You (Voice Input)',
            transcript: speechText,
          })
        );
      }
    }
  }

  private handleMoveToken(e: CustomEvent) {
    const { tokenId, toX, toY } = e.detail;
    this.tokens = this.tokens.map((t) => (t.id === tokenId ? { ...t, x: toX, y: toY } : t));
    const tokenName = this.tokens.find((t) => t.id === tokenId)?.name || 'Token';
    this.events = [
      ...this.events,
      {
        id: String(Date.now()),
        timestamp: new Date().toLocaleTimeString(),
        source: 'system',
        speaker: 'The Watcher',
        text: `${tokenName} moved to (${toX}, ${toY}).`,
        actionType: 'board_move',
      },
    ];

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          type: 'board_move',
          tokenId,
          toX,
          toY,
        })
      );
    }
  }

  render() {
    return html`
      <header>
        <div class="brand">
          <h1>Runefoble</h1>
          <span class="tagline">Imaginative Gaming for Storytellers</span>
        </div>
        <div class="header-actions">
          <runefoble-theme-switcher></runefoble-theme-switcher>
          <button
            style="background:var(--rf-bg-surface); color:var(--rf-text-primary); border:var(--rf-border-width,2px) solid var(--rf-border-color,#121212); box-shadow:var(--rf-shadow-sm,2px 2px 0px #121212); font-weight:700; font-size:0.8rem; padding:4px 10px; cursor:pointer;"
            @click=${() => { this.viewMode = this.viewMode === 'party' ? 'spectator' : 'party'; }}
          >
            ${this.viewMode === 'party' ? '📺 Spectator Mode' : '🎮 Party Mode'}
          </button>
          <div class="session-info">
            <span class="badge-live">● Campaign #4</span>
            <span class="badge-socket ${this.socketConnected ? 'connected' : 'disconnected'}">
              ${this.socketConnected ? '⚡ WebSocket Live' : '○ Standalone'}
            </span>
            <span>Session 14</span>
            <span>DM: The Watcher</span>
          </div>
        </div>
      </header>

      ${this.viewMode === 'spectator'
        ? html`
            <runefoble-spectator-view
              sessionId="14"
              .cols=${8}
              .rows=${8}
              .tokens=${this.tokens.map((t) => ({
                id: t.id,
                name: t.name,
                x: t.x,
                y: t.y,
                color: t.color,
                isAiControlled: t.isAiControlled,
              }))}
              .atmosphere=${{
                location_name: 'Ancient Crypt of the Star-Eater',
                lighting: 'Cold flickering torches',
                mood: 'Suspenseful',
                description: 'Ancient shadows crawl across granite sarcophagi.',
                ambient_audio_prompt: 'dripping water, hollow whispers',
              }}
              .chronicle=${this.events.map((e) => ({
                id: e.id,
                speaker: e.speaker,
                text: e.text,
                timestamp: e.timestamp,
                action_type: e.actionType,
              }))}
              .round=${3}
            ></runefoble-spectator-view>
          `
        : html`
            <div class="layout-grid">
              <runefoble-board
                .cols=${8}
                .rows=${8}
                .tokens=${this.tokens}
                .fogOfWar=${true}
                watcherStatus="${this.isListening ? 'Streaming voice & resolving actions in realtime...' : 'Observing session. Speak to command the board.'}"
                @move-token=${this.handleMoveToken}
              ></runefoble-board>

        <div>
          <runefoble-character-card
            characterName="Kyra the Sun Maiden"
            characterClass="Cleric Lvl 4"
            .isAiStandIn=${true}
            .currentHp=${28}
            .maxHp=${32}
            .armorClass=${16}
            .initiative=${0}
            .speed=${25}
            .conditions=${[
              {
                id: 'pen-1',
                name: 'Drunk (Missed Session)',
                severity: 'moderate',
                source: 'session_penalty',
                description: 'Player missed session! DM penalty applied: +2 bravery, -2 perception.',
              },
              {
                id: 'pen-2',
                name: 'Foolishness',
                severity: 'minor',
                source: 'session_penalty',
                description: 'AI will roleplay boldly without second-guessing danger.',
              },
            ]}
          ></runefoble-character-card>
          <div style="margin-top: 16px;">
            <runefoble-dice-roller
              sessionId="14"
              rollerId="char-kyra"
              rollerName="Kyra the Sun Maiden"
              formula="1d20+4"
            ></runefoble-dice-roller>
          </div>
        </div>

        <runefoble-watcher-feed .events=${this.events}></runefoble-watcher-feed>
      </div>

      <div style="margin-top: 24px;">
        <runefoble-voice-controls
          .isListening=${this.isListening}
          @voice-toggle=${this.toggleListening}
        ></runefoble-voice-controls>
      </div>
      `}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-app': RunefobleApp;
  }
}
