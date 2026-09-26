import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface CampaignOption { id: string; title: string; }

@customElement('runefoble-campaign-nav')
export class RunefobleCampaignNav extends LitElement {
  @property({ type: String }) campaignId = '4';
  @property({ type: String }) campaignTitle = 'Campaign #4';
  @property({ type: String }) sessionId = '14';
  @property({ type: String }) dmName = 'The Watcher';
  @property({ type: String }) userRole = 'Player';
  @property({ type: Boolean }) socketConnected = false;
  @property({ type: Array }) availableCampaigns: CampaignOption[] = [
    { id: '4', title: 'Tomb of the Star-Eater' },
    { id: '5', title: 'Whispering Depths' },
  ];

  @state() private isSelectorOpen = false;

  static styles = css`
    :host { display: inline-flex; align-items: center; position: relative; }
    .session-info { display: flex; align-items: center; gap: 10px; font-size: 0.85rem; flex-wrap: wrap; }
    .badge-live {
      background: var(--rf-bg-surface); color: var(--rf-accent-primary);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow-sm); padding: 4px 10px; font-weight: 700; cursor: pointer;
    }
    .badge-live:hover { transform: translate(-1px, -1px); box-shadow: var(--rf-shadow); }
    .badge-role {
      background: var(--rf-bg-surface); color: var(--rf-accent-secondary);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow-sm); padding: 2px 8px; font-weight: 800; font-size: 0.75rem; text-transform: uppercase;
    }
    .badge-socket {
      font-size: 0.75rem; padding: 4px 10px; border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      background: var(--rf-bg-surface); font-weight: 700; box-shadow: var(--rf-shadow-sm);
    }
    .badge-socket.connected { color: var(--rf-accent-secondary); }
    .badge-socket.disconnected { color: var(--rf-accent-primary); }
    .selector-modal {
      position: absolute; top: calc(100% + 8px); left: 0; background: var(--rf-bg-surface);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow); padding: 12px; z-index: 100; min-width: 220px;
      display: flex; flex-direction: column; gap: 6px;
    }
    .campaign-item {
      padding: 6px 10px; border: 1px solid transparent; background: none; text-align: left;
      cursor: pointer; font-weight: 600; color: var(--rf-text-primary);
    }
    .campaign-item:hover { background: var(--rf-bg-canvas); border-color: var(--rf-border-color); }
  `;

  private selectCampaign(camp: CampaignOption) {
    this.campaignId = camp.id;
    this.campaignTitle = camp.title;
    this.isSelectorOpen = false;
    this.dispatchEvent(new CustomEvent('campaign-changed', {
      detail: { campaignId: camp.id, campaignTitle: camp.title },
      bubbles: true, composed: true,
    }));
  }

  render() {
    return html`
      <div class="session-info">
        <button class="badge-live" aria-haspopup="dialog" aria-expanded="${this.isSelectorOpen}"
          @click=${() => { this.isSelectorOpen = !this.isSelectorOpen; }}>● Campaign #${this.campaignId} ▾</button>
        <span class="badge-role">${this.userRole}</span>
        <span class="badge-socket ${this.socketConnected ? 'connected' : 'disconnected'}">
          ${this.socketConnected ? '⚡ WebSocket Live' : '○ Standalone'}
        </span>
        <span>Session ${this.sessionId}</span>
        <span>DM: ${this.dmName}</span>
      </div>
      ${this.isSelectorOpen ? html`
        <div class="selector-modal" role="dialog" aria-label="Campaign Selector">
          ${this.availableCampaigns.map((c) => html`
            <button class="campaign-item" @click=${() => this.selectCampaign(c)}>
              ${c.title} (#${c.id})
            </button>
          `)}
        </div>
      ` : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-campaign-nav': RunefobleCampaignNav;
  }
}
