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
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      background: var(--rf-bg-surface);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      border-radius: var(--rf-border-radius, 0px);
      padding: 16px;
      color: var(--rf-text-primary);
      width: 420px;
      height: 380px;
      display: flex;
      flex-direction: column;
      box-shadow: var(--rf-shadow);
      box-sizing: border-box;
      transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
    }
    .feed-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 8px;
      border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
      margin-bottom: 8px;
    }
    .feed-title {
      font-size: 0.95rem;
      font-weight: 800;
      color: var(--rf-text-primary);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .live-pill {
      font-size: 0.7rem;
      background: var(--rf-accent-tertiary);
      color: var(--rf-color-dark);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      padding: 2px 6px;
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow-sm);
      font-weight: 700;
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
      border-radius: var(--rf-border-radius, 0px);
      font-size: 0.85rem;
      line-height: 1.4;
      background: var(--rf-bg-card);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      border-left: calc(var(--rf-border-width, 2px) * 2 + 2px) solid var(--rf-accent-secondary);
      box-shadow: var(--rf-shadow-sm);
    }
    .event-watcher {
      border-left-color: var(--rf-accent-primary);
    }
    .event-stand-in {
      border-left-color: var(--rf-accent-tertiary);
    }
    .event-player {
      border-left-color: var(--rf-accent-secondary);
    }
    .event-meta {
      display: flex;
      justify-content: space-between;
      font-size: 0.72rem;
      color: var(--rf-text-muted);
      margin-bottom: 4px;
    }
    .speaker-name {
      font-weight: 800;
      color: var(--rf-text-primary);
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
