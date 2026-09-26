import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface InitiativeCombatant {
  id: string;
  name: string;
  initiativeScore: number;
  isNpc?: boolean;
  hp?: number;
  maxHp?: number;
  armorClass?: number;
  conditions?: string[];
}

@customElement('runefoble-initiative-tracker')
export class RunefobleInitiativeTracker extends LitElement {
  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      color: var(--rf-text-primary);
      background: var(--rf-bg-canvas);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow);
      box-sizing: border-box;
      padding: 16px;
      width: 100%;
      max-width: 440px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
      padding-bottom: 12px;
      margin-bottom: 12px;
    }
    .title {
      font-size: 1.1rem;
      font-weight: 900;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin: 0;
    }
    .status-badge {
      display: inline-block;
      font-size: 0.65rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 2px 6px;
      border: 1px solid var(--rf-border-color);
      background: var(--rf-bg-surface);
      margin-top: 2px;
    }
    .status-badge.in-combat {
      background: var(--rf-accent-primary);
      color: var(--rf-text-inverse);
    }
    .round-badge {
      background: var(--rf-accent-tertiary);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow-sm);
      padding: 4px 10px;
      font-weight: 900;
      font-size: 0.95rem;
      text-transform: uppercase;
    }
    .timer-section {
      background: var(--rf-bg-surface);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      padding: 10px 12px;
      margin-bottom: 14px;
      box-shadow: var(--rf-shadow-sm);
    }
    .timer-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }
    .timer-label {
      font-size: 0.75rem;
      font-weight: 800;
      text-transform: uppercase;
      color: var(--rf-text-muted);
    }
    .timer-digits {
      font-family: ui-monospace, SFMono-Regular, monospace;
      font-size: 1.35rem;
      font-weight: 900;
    }
    .timer-digits.urgent {
      color: var(--rf-accent-primary);
      animation: pulse 1s infinite;
    }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    .progress-bar-bg {
      height: 8px;
      background: var(--rf-bg-inset);
      border: 1px solid var(--rf-border-color);
      overflow: hidden;
      margin-bottom: 8px;
    }
    .progress-bar-fill {
      height: 100%;
      background: var(--rf-accent-secondary);
      transition: width 0.3s ease;
    }
    .progress-bar-fill.urgent { background: var(--rf-accent-primary); }
    .timer-actions { display: flex; gap: 6px; justify-content: flex-end; }
    .btn-sm {
      font-size: 0.7rem;
      font-weight: 800;
      padding: 3px 8px;
      background: var(--rf-bg-canvas);
      border: 1px solid var(--rf-border-color);
      cursor: pointer;
      text-transform: uppercase;
    }
    .btn-sm:hover { background: var(--rf-bg-inset); }
    .btn-sm:active { transform: translate(1px, 1px); }
    .active-banner {
      background: var(--rf-accent-primary);
      color: var(--rf-text-inverse);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow-sm);
      padding: 8px 12px;
      margin-bottom: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .active-tag {
      font-size: 0.65rem;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      opacity: 0.9;
    }
    .active-name { font-size: 1.15rem; font-weight: 900; display: block; }
    .active-stats { font-size: 0.8rem; font-weight: 800; text-align: right; }
    .order-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 16px;
      max-height: 280px;
      overflow-y: auto;
    }
    .order-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      background: var(--rf-bg-surface);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow-sm);
      cursor: pointer;
      transition: background-color 0.15s ease, transform 0.05s ease;
    }
    .order-item:hover { background: var(--rf-bg-canvas); }
    .order-item.active {
      background: var(--rf-bg-card);
      border-color: var(--rf-accent-primary);
      transform: translateX(4px);
    }
    .rank-box {
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 900;
      font-size: 0.75rem;
      background: var(--rf-border-color);
      color: var(--rf-text-inverse);
      border: 1px solid var(--rf-border-color);
    }
    .score-badge {
      background: var(--rf-accent-tertiary);
      color: var(--rf-color-dark);
      font-weight: 900;
      font-size: 0.8rem;
      padding: 2px 6px;
      border: 1px solid var(--rf-border-color);
      min-width: 22px;
      text-align: center;
    }
    .combatant-details {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .combatant-name { font-weight: 800; font-size: 0.9rem; }
    .npc-tag {
      font-size: 0.65rem;
      font-weight: 800;
      text-transform: uppercase;
      padding: 1px 5px;
      border: 1px solid var(--rf-border-color);
      background: var(--rf-bg-inset);
      color: var(--rf-text-muted);
    }
    .empty-state {
      padding: 20px;
      text-align: center;
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--rf-text-muted);
      border: 2px dashed var(--rf-border-color);
    }
    .controls { display: flex; gap: 8px; }
    .btn-main {
      flex: 1;
      background: var(--rf-accent-primary);
      color: var(--rf-text-inverse);
      font-weight: 900;
      font-size: 0.95rem;
      text-transform: uppercase;
      padding: 10px;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow-sm);
      cursor: pointer;
    }
    .btn-main:hover { filter: brightness(0.9); }
    .btn-main:active { transform: translate(2px, 2px); box-shadow: none; }
    .btn-secondary {
      background: var(--rf-bg-surface);
      color: var(--rf-text-primary);
      font-weight: 800;
      font-size: 0.85rem;
      padding: 10px 14px;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow-sm);
      cursor: pointer;
      text-transform: uppercase;
    }
    .btn-secondary:hover { background: var(--rf-bg-canvas); }
    .btn-secondary:active { transform: translate(2px, 2px); box-shadow: none; }
  `;

  @property({ type: String }) sessionId: string = '';
  @property({ type: Number }) roundNumber: number = 1;
  @property({ type: Boolean }) inCombat: boolean = false;
  @property({ type: String }) activeCombatantId: string | null = null;
  @property({ type: Array }) combatants: InitiativeCombatant[] = [];
  @property({ type: Number }) turnSecondsRemaining: number = 60;
  @property({ type: Number }) turnTotalSeconds: number = 60;
  @state() private timerPaused: boolean = false;
  private timerInterval: number | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this.startTimer();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.stopTimer();
  }

  private startTimer(): void {
    this.stopTimer();
    this.timerInterval = window.setInterval(() => {
      if (this.inCombat && !this.timerPaused && this.turnSecondsRemaining > 0) {
        this.turnSecondsRemaining -= 1;
        if (this.turnSecondsRemaining === 0) {
          this.dispatchEvent(
            new CustomEvent('turn-timer-expired', {
              detail: { combatantId: this.activeCombatantId, roundNumber: this.roundNumber },
              bubbles: true,
              composed: true,
            })
          );
        }
      }
    }, 1000);
  }

  private stopTimer(): void {
    if (this.timerInterval !== null) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  private get sortedCombatants(): InitiativeCombatant[] {
    return [...this.combatants].sort((a, b) => {
      if (b.initiativeScore !== a.initiativeScore) {
        return b.initiativeScore - a.initiativeScore;
      }
      if ((a.isNpc ?? false) !== (b.isNpc ?? false)) {
        return a.isNpc ? 1 : -1;
      }
      return a.name.localeCompare(b.name);
    });
  }

  private get activeCombatant(): InitiativeCombatant | undefined {
    const list = this.sortedCombatants;
    if (this.activeCombatantId) {
      return list.find((c) => c.id === this.activeCombatantId);
    }
    return list[0];
  }

  nextTurn(): void {
    const list = this.sortedCombatants;
    if (list.length === 0) return;
    const currId = this.activeCombatantId || list[0].id;
    const currIdx = list.findIndex((c) => c.id === currId);
    const nextIdx = (currIdx + 1) % list.length;
    if (nextIdx === 0) {
      this.roundNumber += 1;
    }
    const previousId = currId;
    this.activeCombatantId = list[nextIdx].id;
    this.turnSecondsRemaining = this.turnTotalSeconds;
    this.dispatchEvent(
      new CustomEvent('initiative-turn-advanced', {
        detail: {
          previousId,
          activeCombatantId: this.activeCombatantId,
          roundNumber: this.roundNumber,
          turnSecondsRemaining: this.turnSecondsRemaining,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  previousTurn(): void {
    const list = this.sortedCombatants;
    if (list.length === 0) return;
    const currId = this.activeCombatantId || list[0].id;
    const currIdx = list.findIndex((c) => c.id === currId);
    const prevIdx = (currIdx - 1 + list.length) % list.length;
    if (currIdx === 0 && this.roundNumber > 1) {
      this.roundNumber -= 1;
    }
    this.activeCombatantId = list[prevIdx].id;
    this.turnSecondsRemaining = this.turnTotalSeconds;
  }

  togglePauseTimer(): void { this.timerPaused = !this.timerPaused; }
  resetTimer(): void { this.turnSecondsRemaining = this.turnTotalSeconds; }
  selectCombatant(id: string): void {
    this.activeCombatantId = id;
    this.turnSecondsRemaining = this.turnTotalSeconds;
  }

  private formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  render() {
    const sorted = this.sortedCombatants;
    const active = this.activeCombatant;
    const effectiveActiveId = active ? active.id : null;
    const isUrgent = this.turnSecondsRemaining <= 10;
    const progressPercent = Math.max(
      0,
      Math.min(100, (this.turnSecondsRemaining / (this.turnTotalSeconds || 60)) * 100)
    );

    return html`
      <div class="header">
        <div>
          <h2 class="title">Initiative</h2>
          <span class="status-badge ${this.inCombat ? 'in-combat' : ''}">
            ${this.inCombat ? 'In Combat' : 'Encounter Lobby'}
          </span>
        </div>
        <div class="round-badge">Round ${this.roundNumber}</div>
      </div>

      <div class="timer-section">
        <div class="timer-header">
          <span class="timer-label">Turn Timer</span>
          <span class="timer-digits ${isUrgent ? 'urgent' : ''}">
            ${this.formatTime(this.turnSecondsRemaining)}
          </span>
        </div>
        <div class="progress-bar-bg">
          <div
            class="progress-bar-fill ${isUrgent ? 'urgent' : ''}"
            style="width: ${progressPercent}%;"
          ></div>
        </div>
        <div class="timer-actions">
          <button class="btn-sm" @click=${this.togglePauseTimer}>
            ${this.timerPaused ? 'Resume' : 'Pause'}
          </button>
          <button class="btn-sm" @click=${this.resetTimer}>Reset</button>
        </div>
      </div>

      ${active ? html`
        <div class="active-banner">
          <div>
            <span class="active-tag">Active Turn</span>
            <span class="active-name">${active.name}</span>
          </div>
          <div class="active-stats">
            ${active.armorClass ? html`<div>AC ${active.armorClass}</div>` : ''}
            ${active.hp !== undefined ? html`<div>HP ${active.hp}/${active.maxHp ?? active.hp}</div>` : ''}
          </div>
        </div>
      ` : ''}

      <div class="order-list">
        ${sorted.length === 0
          ? html`<div class="empty-state">No combatants in initiative order.</div>`
          : sorted.map((c, idx) => {
              const isActive = c.id === effectiveActiveId;
              return html`
                <div
                  class="order-item ${isActive ? 'active' : ''}"
                  @click=${() => this.selectCombatant(c.id)}
                >
                  <div class="rank-box">${idx + 1}</div>
                  <div class="score-badge">${c.initiativeScore}</div>
                  <div class="combatant-details">
                    <span class="combatant-name">${c.name}</span>
                    ${c.isNpc ? html`<span class="npc-tag">NPC</span>` : ''}
                  </div>
                </div>
              `;
            })}
      </div>

      <div class="controls">
        <button class="btn-secondary" @click=${this.previousTurn}>◀ Prev</button>
        <button class="btn-main" @click=${this.nextTurn}>Next Turn ▶</button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-initiative-tracker': RunefobleInitiativeTracker;
  }
}
