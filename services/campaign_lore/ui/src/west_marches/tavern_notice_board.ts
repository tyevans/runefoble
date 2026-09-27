import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { WestMarchesNotice } from './types.ts';

@customElement('runefoble-tavern-notice-board')
export class RunefobleTavernNoticeBoard extends LitElement {
  // Use light DOM rendering or host styling so it inherits parent container styles
  createRenderRoot() { return this; }

  @property({ type: Array }) notices: WestMarchesNotice[] = [];
  @state() private noticeFilter = 'all';

  render() {
    const visible = this.notices.filter((n) => this.noticeFilter === 'all' || n.notice_type === this.noticeFilter);
    return html`
      <div class="tavern-view">
        <div class="tavern-controls">
          <div style="font-weight: 800; font-size: 1.1rem;">🍺 The Communal Tavern Notice Board</div>
          <select class="filter-select" .value=${this.noticeFilter} @change=${(e: Event) => (this.noticeFilter = (e.target as HTMLSelectElement).value)}>
            <option value="all">All Notices</option>
            <option value="bounty">Bounties</option>
            <option value="rumor">Rumors</option>
            <option value="request">Expedition Requests</option>
          </select>
        </div>
        <div class="notice-grid">
          ${visible.map((n) => html`
            <div class="notice-card">
              <span class="notice-type-tag ${n.notice_type}">${n.notice_type}</span>
              <h4 class="notice-title">${n.title}</h4>
              <div class="notice-body">${n.content}</div>
              ${n.bounty_reward ? html`<div class="bounty-reward">🪙 Bounty: ${n.bounty_reward} Gold</div>` : ''}
              <div class="notice-meta">Posted by ${n.author_name} ${n.party_name ? `(${n.party_name})` : ''}</div>
            </div>
          `)}
        </div>
      </div>
    `;
  }
}
