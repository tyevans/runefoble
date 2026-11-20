import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { absenteeDirectiveStyles } from './runefoble-absentee-directive.styles.ts';
import './runefoble-absentee-vote-card.ts';
import type { DecisionPoll } from './runefoble-absentee-vote-card.ts';
import { TACTICAL_STANCES, type TacticalStance } from './absentee-stances.ts';

@customElement('runefoble-absentee-directive')
export class RunefobleAbsenteeDirective extends LitElement {
  /** The bound character's name. The App Shell passes it. The component has no default name. */
  @property({ type: String }) characterName = '';
  @property({ type: String }) characterClass = '';
  /** True only while the character is an active stand-in. The App Shell passes the real flag. */
  @property({ type: Boolean }) standInActive = false;
  /** The saved stance id, or '' when the player has not chosen one. The App Shell owns the value. */
  @property({ type: String }) currentStance = '';
  @property({ type: Array }) penalties: string[] = [];
  @property({ type: Number }) currentHp = 0;
  @property({ type: Number }) maxHp = 0;
  @property({ type: Object }) activePoll: DecisionPoll | null = null;
  @property({ type: Boolean }) hapticFeedbackEnabled = true;
  @property({ type: Array }) stances: TacticalStance[] = TACTICAL_STANCES;

  static styles = absenteeDirectiveStyles;

  public triggerHaptic(pattern: number[] = [60]): void {
    if (!this.hapticFeedbackEnabled) return;
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      try { navigator.vibrate(pattern); } catch { /* unsupported */ }
    }
    this.dispatchEvent(new CustomEvent('haptic-pulse', {
      detail: { pattern, target: 'directive-stance' }, bubbles: true, composed: true,
    }));
  }

  /**
   * Asks the host to save a stance. The component does not change `currentStance`. The host saves
   * the stance on the server and sets the new value only after the server confirms it.
   */
  public selectStance(stanceId: string): void {
    this.triggerHaptic([60]);
    const detail = { characterName: this.characterName, stance: stanceId };
    this.dispatchEvent(new CustomEvent('stance-selected', { detail, bubbles: true, composed: true }));
  }

  private handleVoteCast(event: CustomEvent): void {
    this.dispatchEvent(new CustomEvent('decision-voted', {
      detail: event.detail, bubbles: true, composed: true,
    }));
  }

  render() {
    return html`
      <div class="container">
        <div class="header">
          <div class="title-group">
            <h2 class="title">${this.characterName}</h2>
            <span class="char-info">${this.characterClass || 'Adventurer'}</span>
          </div>
          <span class="status-pill ${this.standInActive ? 'active' : 'offline'}">
            ${this.standInActive ? 'Stand-In Active' : 'Player Present'}
          </span>
        </div>

        ${this.maxHp > 0 ? html`
          <div class="vitals-bar">
            <span>HP: <span class="vitals-hp">${this.currentHp} / ${this.maxHp}</span></span>
            <span>Directive: <span class="vitals-stance">${this.currentStance || 'No stance set'}</span></span>
          </div>
        ` : ''}

        ${this.penalties.length > 0 ? html`
          <div class="section-label">Active Absence Penalties</div>
          <div class="penalties-bar">
            ${this.penalties.map((p) => html`<span class="penalty-tag">⚠️ ${p}</span>`)}
          </div>
        ` : ''}

        <div class="section-label">Tactical Posture Directive</div>
        <div class="stance-carousel" role="radiogroup" aria-label="Tactical Stances">
          ${this.stances.map((s) => html`
            <button
              class="stance-btn ${this.currentStance === s.id ? 'active' : ''}"
              role="radio"
              aria-checked="${this.currentStance === s.id}"
              @click=${() => this.selectStance(s.id)}
            >
              <span class="stance-icon">${s.icon}</span>
              <span class="stance-name">${s.name}</span>
              <span class="stance-desc">${s.description}</span>
            </button>
          `)}
        </div>

        ${this.activePoll ? html`
          <div class="section-label">Active Party Decision</div>
          <div class="vote-section">
            <runefoble-absentee-vote-card
              .poll=${this.activePoll}
              .hapticFeedbackEnabled=${this.hapticFeedbackEnabled}
              @vote-cast=${this.handleVoteCast}
            ></runefoble-absentee-vote-card>
          </div>
        ` : ''}

      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-absentee-directive': RunefobleAbsenteeDirective;
  }
}
