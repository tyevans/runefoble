import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

export interface WatcherFeedEvent {
  id: string;
  timestamp: string;
  source: 'player' | 'watcher_dm' | 'stand_in' | 'system';
  speaker: string;
  text: string;
  actionType?: 'speech' | 'dice_roll' | 'board_move' | 'dm_ruling';
}

@customElement('runefoble-watcher-feed')
export class RunefobleWatcherFeed extends LitElement {
  static styles = css`
    :host {
      display: block;
      font-family: system-ui, -apple-system, sans-serif;
      background: #090d16;
      border: 1px solid #1e293b;
      border-radius: 12px;
      padding: 16px;
      color: #f1f5f9;
      width: 420px;
      height: 380px;
      display: flex;
      flex-direction: column;
    }
    .feed-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 8px;
      border-bottom: 1px solid #1e293b;
      margin-bottom: 8px;
    }
    .feed-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: #a855f7;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .live-pill {
      font-size: 0.7rem;
      background: #14532d;
      color: #86efac;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
    }
    .event-list {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding-right: 4px;
    }
    .event-item {
      padding: 8px 10px;
      border-radius: 8px;
      font-size: 0.85rem;
      line-height: 1.4;
      background: #0f172a;
      border-left: 3px solid #64748b;
    }
    .event-watcher {
      background: #1e1b4b;
      border-left-color: #8b5cf6;
    }
    .event-stand-in {
      background: #2e1065;
      border-left-color: #ec4899;
    }
    .event-player {
      background: #0f172a;
      border-left-color: #38bdf8;
    }
    .event-meta {
      display: flex;
      justify-content: space-between;
      font-size: 0.72rem;
      color: #94a3b8;
      margin-bottom: 4px;
    }
    .speaker-name {
      font-weight: 700;
      color: #e2e8f0;
    }
  `;

  @property({ type: Array }) events: WatcherFeedEvent[] = [];

  render() {
    return html`
      <div class="feed-header">
        <div class="feed-title">
          <span>🔮 The Watcher Chronicle</span>
        </div>
        <div class="live-pill">● LIVE STREAM</div>
      </div>

      <div class="event-list">
        ${this.events.map(
          (evt) => html`
            <div
              class="event-item ${evt.source === 'watcher_dm'
                ? 'event-watcher'
                : evt.source === 'stand_in'
                ? 'event-stand-in'
                : 'event-player'}"
            >
              <div class="event-meta">
                <span class="speaker-name">${evt.speaker}</span>
                <span>${evt.timestamp}</span>
              </div>
              <div>${evt.text}</div>
            </div>
          `
        )}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-watcher-feed': RunefobleWatcherFeed;
  }
}
