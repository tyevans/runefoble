/**
 * Lit Web Component: <runefoble-audience-studio>
 * Governed by ADR-0004, ADR-0012, and ADR-0013.
 */

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { audienceStudioStyles } from './runefoble-audience-studio.styles.ts';

export interface PollOptionItem {
  id: string;
  label: string;
  votes: number;
}

export interface ActivePollData {
  id: string;
  title: string;
  prompt: string;
  options: PollOptionItem[];
  totalVotes: number;
  quorum: number;
  status: string;
}

export interface ProposalItem {
  id: string;
  title: string;
  description: string;
  modifierType: string;
  status: string;
}

@customElement('runefoble-audience-studio')
export class RunefobleAudienceStudio extends LitElement {
  static styles = [audienceStudioStyles];

  @property({ type: String }) campaignId = 'campaign-1';
  @property({ type: String }) sessionId = 'session-1';
  @property({ type: String }) userId = 'spectator-1';
  @property({ type: Boolean }) isDM = false;
  @property({ type: Boolean }) wsConnected = false;
  @property({ type: Object }) activePoll: ActivePollData | null = null;
  @property({ type: Array }) proposals: ProposalItem[] = [];

  @state() private votedOptionId: string | null = null;

  private handleVote(optionId: string) {
    if (!this.activePoll || this.votedOptionId) return;
    this.votedOptionId = optionId;
    this.dispatchEvent(
      new CustomEvent('vote-cast', {
        detail: {
          pollId: this.activePoll.id,
          optionId,
          voterId: this.userId,
          campaignId: this.campaignId,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleApprove(proposalId: string) {
    this.dispatchEvent(
      new CustomEvent('proposal-approved', {
        detail: { proposalId, dmUserId: this.userId, campaignId: this.campaignId },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleVeto(proposalId: string) {
    this.dispatchEvent(
      new CustomEvent('proposal-vetoed', {
        detail: { proposalId, dmUserId: this.userId, campaignId: this.campaignId },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    return html`
      <div class="header">
        <div class="title">Audience Studio</div>
        <span class="status-badge ${this.wsConnected ? 'live' : 'offline'}">
          ${this.wsConnected ? 'Live' : 'Offline'}
        </span>
      </div>

      ${this.activePoll ? this.renderPoll(this.activePoll) : html`
        <div class="poll-prompt">No active chaos poll. Waiting for DM or trigger...</div>
      `}

      ${this.isDM && this.proposals.length > 0 ? html`
        <div class="section">
          <div class="section-title">DM Chaos Moderation Queue</div>
          ${this.proposals.map((prop) => this.renderProposal(prop))}
        </div>
      ` : ''}
    `;
  }

  private renderPoll(poll: ActivePollData) {
    const total = poll.totalVotes > 0 ? poll.totalVotes : 1;
    return html`
      <div class="poll-card">
        <div class="poll-title">${poll.title}</div>
        <div class="poll-prompt">${poll.prompt} (Quorum: ${poll.quorum})</div>
        ${poll.options.map((opt) => {
          const pct = Math.round((opt.votes / total) * 100);
          return html`
            <div class="option-row">
              <button
                class="option-btn"
                ?disabled=${this.votedOptionId !== null}
                @click=${() => this.handleVote(opt.id)}
              >
                <span>${opt.label}</span>
                <span>${opt.votes} (${pct}%)</span>
              </button>
              <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: ${pct}%"></div>
              </div>
            </div>
          `;
        })}
      </div>
    `;
  }

  private renderProposal(prop: ProposalItem) {
    return html`
      <div class="proposal-card">
        <div class="poll-title">${prop.title}</div>
        <div class="poll-prompt">${prop.description}</div>
        <div class="btn-row">
          <button class="btn btn-approve" @click=${() => this.handleApprove(prop.id)}>
            Approve Chaos
          </button>
          <button class="btn btn-veto" @click=${() => this.handleVeto(prop.id)}>
            Veto
          </button>
        </div>
      </div>
    `;
  }
}
