import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import './components/runefoble-board.ts';
import './components/runefoble-character-card.ts';
import './components/runefoble-watcher-feed.ts';
import type { BoardToken } from './components/runefoble-board.ts';
import type { WatcherFeedEvent } from './components/runefoble-watcher-feed.ts';

@customElement('runefoble-app')
export class RunefobleApp extends LitElement {
  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background-color: #0b0f19;
      color: #f8fafc;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 24px;
      box-sizing: border-box;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      border-bottom: 1px solid #1e293b;
      margin-bottom: 24px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand h1 {
      font-size: 1.8rem;
      margin: 0;
      background: linear-gradient(135deg, #38bdf8, #818cf8, #c084fc);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.5px;
    }
    .tagline {
      font-size: 0.9rem;
      color: #94a3b8;
    }
    .session-info {
      display: flex;
      align-items: center;
      gap: 16px;
      font-size: 0.85rem;
    }
    .badge-live {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid #059669;
      padding: 4px 12px;
      border-radius: 9999px;
      font-weight: 600;
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
    .voice-control-panel {
      margin-top: 24px;
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .mic-button {
      background: linear-gradient(135deg, #ef4444, #dc2626);
      color: white;
      border: none;
      border-radius: 8px;
      padding: 10px 20px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: opacity 0.2s;
    }
    .mic-button:hover {
      opacity: 0.9;
    }
    .mic-button.listening {
      background: linear-gradient(135deg, #10b981, #059669);
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
      70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
      100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }
  `;

  @state() private isListening = false;
  @state() private tokens: BoardToken[] = [
    { id: '1', name: 'Valeros', x: 2, y: 3, color: '#2563eb' },
    { id: '2', name: 'Kyra (AI Stand-in)', x: 3, y: 3, isAiControlled: true, color: '#db2777' },
    { id: '3', name: 'Goblin Scout', x: 5, y: 1, color: '#16a34a' },
    { id: '4', name: 'Red Dragon Wyrmling', x: 6, y: 5, color: '#dc2626' },
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

  private toggleListening() {
    this.isListening = !this.isListening;
    if (this.isListening) {
      this.events = [
        ...this.events,
        {
          id: String(Date.now()),
          timestamp: new Date().toLocaleTimeString(),
          source: 'player',
          speaker: 'You (Voice Input)',
          text: '"Speak and the board obeys! Moving to engage the Goblin Scout."',
          actionType: 'speech',
        },
      ];
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
  }

  render() {
    return html`
      <header>
        <div class="brand">
          <h1>Runefoble</h1>
          <span class="tagline">Imaginative Gaming for Storytellers</span>
        </div>
        <div class="session-info">
          <span class="badge-live">● Campaign #4: Tomb of the Star-Eater</span>
          <span>Session 14</span>
          <span>DM: The Watcher (Voice AI)</span>
        </div>
      </header>

      <div class="layout-grid">
        <runefoble-board
          .cols=${8}
          .rows=${8}
          .tokens=${this.tokens}
          watcherStatus="${this.isListening ? 'Streaming voice & resolving actions in realtime...' : 'Observing session. Speak to command the board.'}"
          @move-token=${this.handleMoveToken}
        ></runefoble-board>

        <div>
          <runefoble-character-card
            characterName="Kyra the Sun Maiden"
            characterClass="Cleric Lvl 4"
            .isAiStandIn=${true}
            .currentHp=${26}
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
        </div>

        <runefoble-watcher-feed .events=${this.events}></runefoble-watcher-feed>
      </div>

      <div class="voice-control-panel">
        <div>
          <strong>Collaborative Voice Channel</strong>
          <div style="font-size: 0.85rem; color: #94a3b8;">
            Speak naturally: "Move my warrior to the chest", "Cast cure wounds on Valeros", "What does the altar look like?"
          </div>
        </div>
        <button
          class="mic-button ${this.isListening ? 'listening' : ''}"
          @click=${this.toggleListening}
        >
          🎙️ ${this.isListening ? 'Streaming Audio (Click to Mute)' : 'Push to Talk'}
        </button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-app': RunefobleApp;
  }
}
