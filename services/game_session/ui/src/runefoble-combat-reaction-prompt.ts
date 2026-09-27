import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { reactionPromptStyles } from './runefoble-combat-reaction-prompt.styles.ts';

export interface ReactionOption {
  id: string;
  label: string;
  actionTaken: string;
  badge?: string;
  details?: Record<string, unknown>;
}

@customElement('runefoble-combat-reaction-prompt')
export class RunefobleCombatReactionPrompt extends LitElement {
  static styles = [reactionPromptStyles];

  @property({ type: String }) sessionId = '';
  @property({ type: String }) reactionId = '';
  @property({ type: String }) reactingCombatantId = '';
  @property({ type: String }) reactingCombatantName = 'Combatant';
  @property({ type: String }) triggerPhrase = '';
  @property({ type: String }) reactionType = 'reaction';
  @property({ type: String }) targetId = '';
  @property({ type: Number }) timeoutSeconds = 15;
  @property({ type: Number }) secondsRemaining = 15;
  @property({ type: Boolean }) isOpen = true;
  @property({ type: String }) status: 'active' | 'resolved' | 'declined' | 'expired' = 'active';
  @property({ type: String }) resolvedAction = '';
  @property({ type: Array }) options: ReactionOption[] = [];
  @state() private timerId: number | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    if (this.status === 'active') this.startTimer();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.stopTimer();
  }

  private startTimer(): void {
    this.stopTimer();
    this.timerId = window.setInterval(() => {
      if (this.status !== 'active') return this.stopTimer();
      if (this.secondsRemaining > 0) {
        this.secondsRemaining -= 1;
        if (this.secondsRemaining === 0) {
          this.status = 'expired';
          this.stopTimer();
          this.dispatchEvent(new CustomEvent('reaction-timeout', {
            detail: { sessionId: this.sessionId, reactionId: this.reactionId },
            bubbles: true, composed: true,
          }));
        }
      }
    }, 1000);
  }

  private stopTimer(): void {
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }

  private get effectiveOptions(): ReactionOption[] {
    if (this.options?.length) return this.options;
    const map: Record<string, ReactionOption[]> = {
      shield: [{ id: 'shield', label: 'Cast Shield (+5 AC)', actionTaken: 'cast_shield', badge: '-1 Slot', details: { spell: 'Shield', ac_bonus: 5 } }],
      counterspell: [{ id: 'counterspell', label: 'Counterspell Trigger', actionTaken: 'counterspell', badge: '3rd Level', details: { spell: 'Counterspell' } }],
      opportunity_attack: [{ id: 'oa', label: 'Opportunity Attack', actionTaken: 'opportunity_attack', badge: 'Melee Strike' }],
      hellish_rebuke: [{ id: 'hellish_rebuke', label: 'Hellish Rebuke (2d10 Fire)', actionTaken: 'hellish_rebuke', badge: '-1 Slot' }],
      uncanny_dodge: [{ id: 'uncanny_dodge', label: 'Uncanny Dodge (Halve Damage)', actionTaken: 'uncanny_dodge', badge: 'Rogue Feature' }],
    };
    return map[this.reactionType] ?? [{ id: 'execute', label: `Execute ${this.reactionType}`, actionTaken: this.reactionType, badge: 'Standard' }];
  }

  resolveOption(option: ReactionOption): void {
    this.status = 'resolved';
    this.resolvedAction = option.label;
    this.stopTimer();
    this.dispatchEvent(new CustomEvent('reaction-resolved', {
      detail: { sessionId: this.sessionId, reactionId: this.reactionId, combatantId: this.reactingCombatantId, actionTaken: option.actionTaken, details: option.details ?? {} },
      bubbles: true, composed: true,
    }));
  }

  decline(): void {
    this.status = 'declined';
    this.resolvedAction = 'Declined';
    this.stopTimer();
    this.dispatchEvent(new CustomEvent('reaction-resolved', {
      detail: { sessionId: this.sessionId, reactionId: this.reactionId, combatantId: this.reactingCombatantId, actionTaken: 'decline' },
      bubbles: true, composed: true,
    }));
  }

  render() {
    if (!this.isOpen) return html``;
    const isUrgent = this.secondsRemaining <= 5 && this.status === 'active';
    const percent = Math.max(0, Math.min(100, (this.secondsRemaining / (this.timeoutSeconds || 15)) * 100));

    return html`
      <div class="modal-backdrop" role="dialog" aria-modal="true" aria-label="Reaction Interrupt Prompt">
        <div class="modal-card">
          <div class="urgent-header">
            <h2 class="urgent-title">⚡ Turn Paused: Reaction</h2>
            <span class="status-badge ${this.status}">${this.status}</span>
          </div>
          ${this.status === 'active' ? html`
            <div class="timer-box">
              <div class="timer-row"><span>Time to React</span><span class="timer-countdown ${isUrgent ? 'urgent' : ''}">${this.secondsRemaining}s</span></div>
              <div class="countdown-track"><div class="countdown-fill ${isUrgent ? 'urgent' : ''}" style="width: ${percent}%"></div></div>
            </div>
            <div class="trigger-banner">
              <div class="trigger-who">${this.reactingCombatantName} shouted:</div>
              <div class="trigger-quote">"${this.triggerPhrase || this.reactionType}"</div>
            </div>
            <div class="actions-list">
              ${this.effectiveOptions.map((opt, i) => html`
                <button class="btn-action ${i === 0 ? 'primary' : ''}" @click=${() => this.resolveOption(opt)}>
                  <span>${opt.label}</span>
                  ${opt.badge ? html`<span class="status-badge">${opt.badge}</span>` : ''}
                </button>
              `)}
              <button class="decline-btn" @click=${this.decline}>Decline / Pass Reaction</button>
            </div>
          ` : html`
            <div class="resolution-toast">
              ${this.status === 'resolved' ? html`Reaction Resolved: ${this.resolvedAction}` : ''}
              ${this.status === 'declined' ? html`Reaction Declined — Resuming Combat Turn` : ''}
              ${this.status === 'expired' ? html`Reaction Window Expired — Turn Resumed` : ''}
            </div>
          `}
        </div>
      </div>
    `;
  }
}
