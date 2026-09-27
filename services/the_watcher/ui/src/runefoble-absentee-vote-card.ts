import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface VoteOption {
  id: string;
  label: string;
  votes?: number;
}

export interface DecisionPoll {
  id: string;
  title: string;
  description: string;
  options: VoteOption[];
  expiresInSeconds?: number;
}

@customElement('runefoble-absentee-vote-card')
export class RunefobleAbsenteeVoteCard extends LitElement {
  @property({ type: Object }) poll: DecisionPoll | null = null;
  @property({ type: String }) selectedOptionId: string | null = null;
  @property({ type: Boolean }) hasVoted = false;
  @property({ type: Boolean }) hapticFeedbackEnabled = true;
  @state() private hapticStatus = '';

  static styles = css`
    :host {
      display: block; background: var(--rf-bg-surface-raised, #1a1b1f);
      border: 1px solid var(--rf-border-color, #3b3e47); padding: 12px;
      border-radius: 6px; font-family: var(--rf-font-family, system-ui, sans-serif);
      color: var(--rf-text-primary, #f5f7fa);
    }
    .poll-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; gap: 8px; }
    .poll-title { font-size: 0.95rem; font-weight: 700; margin: 0; }
    .poll-timer {
      font-family: var(--rf-font-mono, monospace); font-size: 0.7rem;
      background: #1e1b4b; color: #c7d2fe; padding: 2px 6px; border-radius: 4px;
    }
    .poll-desc { font-size: 0.8rem; color: var(--rf-text-secondary, #a0a5b2); margin: 0 0 10px 0; line-height: 1.35; }
    .options-grid { display: flex; flex-direction: column; gap: 8px; }
    .vote-option-btn {
      min-height: 48px; padding: 8px 12px; background: var(--rf-bg-surface, #121316);
      border: 1px solid var(--rf-border-color, #3b3e47); color: var(--rf-text-primary, #f5f7fa);
      font-weight: 600; font-size: 0.85rem; border-radius: 4px; display: flex;
      justify-content: space-between; align-items: center; cursor: pointer; transition: all 0.15s ease;
    }
    .vote-option-btn:hover:not(:disabled) { border-color: var(--rf-color-accent, #3b82f6); }
    .vote-option-btn.selected { border-color: var(--rf-color-accent, #3b82f6); background: rgba(59, 130, 246, 0.2); }
    .vote-option-btn:disabled { opacity: 0.75; cursor: default; }
    .vote-count { font-family: var(--rf-font-mono, monospace); font-size: 0.75rem; color: var(--rf-text-secondary, #a0a5b2); }
    .feedback-pill { margin-top: 8px; font-size: 0.72rem; color: #10b981; font-family: var(--rf-font-mono, monospace); text-align: center; }
    .empty { font-style: italic; color: var(--rf-text-secondary, #a0a5b2); font-size: 0.8rem; }
  `;

  public triggerHaptic(pattern: number[] = [100, 50, 100]): void {
    if (!this.hapticFeedbackEnabled) return;
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      try { navigator.vibrate(pattern); } catch { /* unsupported */ }
    }
    this.dispatchEvent(new CustomEvent('haptic-pulse', {
      detail: { pattern, target: 'vote-card' }, bubbles: true, composed: true,
    }));
  }

  private handleVote(optionId: string): void {
    if (this.hasVoted) return;
    this.selectedOptionId = optionId;
    this.hasVoted = true;
    this.triggerHaptic([100, 50, 100]);
    this.hapticStatus = 'Tactile pulse sent • Vote recorded';
    this.dispatchEvent(new CustomEvent('vote-cast', {
      detail: { pollId: this.poll?.id, optionId }, bubbles: true, composed: true,
    }));
  }

  render() {
    if (!this.poll) return html`<div class="empty">No active party decisions pending.</div>`;
    return html`
      <div class="poll-header">
        <h3 class="poll-title">${this.poll.title}</h3>
        ${this.poll.expiresInSeconds !== undefined ? html`<span class="poll-timer">⏱️ ${this.poll.expiresInSeconds}s</span>` : ''}
      </div>
      <p class="poll-desc">${this.poll.description}</p>
      <div class="options-grid">
        ${this.poll.options.map((opt) => html`
          <button class="vote-option-btn ${this.selectedOptionId === opt.id ? 'selected' : ''}" ?disabled=${this.hasVoted} @click=${() => this.handleVote(opt.id)}>
            <span>${opt.label}</span>
            ${opt.votes !== undefined ? html`<span class="vote-count">${opt.votes} votes</span>` : ''}
          </button>
        `)}
      </div>
      ${this.hasVoted ? html`<div class="feedback-pill">${this.hapticStatus || 'Vote recorded'}</div>` : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-absentee-vote-card': RunefobleAbsenteeVoteCard;
  }
}
