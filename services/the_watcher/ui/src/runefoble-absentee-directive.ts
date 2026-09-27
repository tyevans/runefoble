import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { absenteeDirectiveStyles } from './runefoble-absentee-directive.styles.ts';
import './runefoble-absentee-vote-card.ts';
import type { DecisionPoll } from './runefoble-absentee-vote-card.ts';

export interface TacticalStance {
  id: string;
  name: string;
  icon: string;
  description: string;
}

export const DEFAULT_STANCES: TacticalStance[] = [
  { id: 'defensive', name: 'Defensive', icon: '🛡️', description: 'Protect allies & avoid melee' },
  { id: 'cautious', name: 'Cautious', icon: '⚖️', description: 'Conserve slots & ranged support' },
  { id: 'heroic', name: 'Heroic', icon: '⚔️', description: 'Bold smites & frontline focus' },
];

@customElement('runefoble-absentee-directive')
export class RunefobleAbsenteeDirective extends LitElement {
  @property({ type: String }) characterName = 'Sarah';
  @property({ type: String }) characterClass = 'Cleric';
  @property({ type: Boolean }) standInActive = true;
  @property({ type: String }) currentStance = 'defensive';
  @property({ type: Array }) penalties: string[] = [];
  @property({ type: Number }) currentHp = 0;
  @property({ type: Number }) maxHp = 0;
  @property({ type: Object }) activePoll: DecisionPoll | null = null;
  @property({ type: Boolean }) hapticFeedbackEnabled = true;
  @property({ type: Array }) stances: TacticalStance[] = DEFAULT_STANCES;
  @state() private lastHapticNotice = '';

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

  public selectStance(stanceId: string): void {
    this.currentStance = stanceId;
    this.triggerHaptic([60]);
    this.lastHapticNotice = `Tactical stance shifted to ${stanceId.toUpperCase()}`;
    const detail = { characterName: this.characterName, stance: stanceId };
    this.dispatchEvent(new CustomEvent('directive-changed', { detail, bubbles: true, composed: true }));
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
            <span>Directive: <span class="vitals-stance">${this.currentStance}</span></span>
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

        ${this.lastHapticNotice ? html`
          <div class="haptic-alert">⚡ ${this.lastHapticNotice}</div>
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
