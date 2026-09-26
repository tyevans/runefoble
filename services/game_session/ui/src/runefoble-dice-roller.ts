import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { parseAndRoll, type DiceRollResult } from './utils/dice.ts';

export type RollMode = 'normal' | 'advantage' | 'disadvantage';

const DICE_OPTIONS = [
  { sides: 4, label: 'D4', symbol: '▲' },
  { sides: 6, label: 'D6', symbol: '◼' },
  { sides: 8, label: 'D8', symbol: '◆' },
  { sides: 10, label: 'D10', symbol: '⬟' },
  { sides: 12, label: 'D12', symbol: '⬡' },
  { sides: 20, label: 'D20', symbol: '⬢' },
  { sides: 100, label: 'D100', symbol: '⬤%' },
];

@customElement('runefoble-dice-roller')
export class RunefobleDiceRoller extends LitElement {
  @property({ type: String }) sessionId = 'session-1';
  @property({ type: String }) rollerId = 'player-1';
  @property({ type: String }) rollerName = 'Hero';
  @property({ type: String }) formula = '1d20';
  @property({ type: Object }) forcedResult: DiceRollResult | null = null;

  @state() private selectedSides: number = 20;
  @state() private mode: RollMode = 'normal';
  @state() private formulaInput: string = '1d20';
  @state() private isRolling: boolean = false;
  @state() private lastResult: DiceRollResult | null = null;
  @state() private errorMessage: string = '';

  static styles = css`
    :host { display: block; font-family: var(--rf-font-family, system-ui, sans-serif); color: var(--rf-text-primary, #121212); box-sizing: border-box; }
    .roller-card { background: var(--rf-bg-surface, #ffffff); border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212); border-radius: var(--rf-border-radius, 0px); box-shadow: var(--rf-shadow, 4px 4px 0px #121212); padding: 18px; max-width: 520px; margin: 0 auto; }
    .card-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--rf-border-color, #121212); padding-bottom: 10px; margin-bottom: 14px; }
    .card-header h2 { margin: 0; font-size: 1.15rem; font-weight: 900; text-transform: uppercase; display: flex; align-items: center; gap: 8px; }
    .badge-icon { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; background: var(--rf-color-yellow, #ffb703); border: 2px solid var(--rf-border-color, #121212); font-size: 0.85rem; }
    .section-label { font-size: 0.72rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; color: var(--rf-text-muted, #4b5563); }
    .dice-chips-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
    .dice-chip { background: var(--rf-bg-surface, #ffffff); border: 2px solid var(--rf-border-color, #121212); font-weight: 800; font-size: 0.82rem; padding: 5px 10px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212); transition: transform 0.1s ease; }
    .dice-chip:hover { background: #f0f0f0; }
    .dice-chip.active { background: var(--rf-color-blue, #1d3557); color: #ffffff; transform: translate(1px, 1px); box-shadow: 1px 1px 0px #121212; }
    .mode-toggles { display: flex; gap: 6px; margin-bottom: 14px; }
    .mode-btn { flex: 1; padding: 7px 4px; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; border: 2px solid var(--rf-border-color, #121212); background: var(--rf-bg-surface, #ffffff); cursor: pointer; box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212); }
    .mode-btn.active[data-mode="normal"] { background: var(--rf-border-color, #121212); color: #fff; }
    .mode-btn.active[data-mode="advantage"] { background: var(--rf-color-yellow, #ffb703); color: #121212; }
    .mode-btn.active[data-mode="disadvantage"] { background: var(--rf-color-red, #e63946); color: #fff; }
    .formula-row { display: flex; gap: 8px; margin-bottom: 14px; }
    .formula-input { flex: 1; padding: 8px 10px; font-size: 0.95rem; font-weight: 700; font-family: monospace; border: 2px solid var(--rf-border-color, #121212); background: #fff; }
    .roll-action-btn { padding: 8px 18px; background: var(--rf-color-red, #e63946); color: #ffffff; font-size: 0.95rem; font-weight: 900; text-transform: uppercase; border: 2px solid var(--rf-border-color, #121212); box-shadow: var(--rf-shadow, 4px 4px 0px #121212); cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: transform 0.1s ease, box-shadow 0.1s ease; }
    .roll-action-btn:active, .roll-action-btn.rolling { transform: translate(2px, 2px); box-shadow: 2px 2px 0px #121212; }
    .tumble-animation { display: inline-block; animation: tumble 0.35s infinite linear; }
    @keyframes tumble { 0% { transform: rotate(0deg) scale(1); } 50% { transform: rotate(180deg) scale(1.15); } 100% { transform: rotate(360deg) scale(1); } }
    .result-container { border: 2px solid var(--rf-border-color, #121212); background: var(--rf-bg-surface, #ffffff); padding: 14px; position: relative; overflow: hidden; }
    .result-container.crit { background: #fffdf0; }
    .result-container.fumble { border: 3px solid var(--rf-color-red, #e63946); background: #fff0f0; }
    .banner-crit { background: var(--rf-color-yellow, #ffb703); color: #121212; font-weight: 900; font-size: 0.82rem; text-align: center; padding: 5px; margin: -14px -14px 10px -14px; border-bottom: 2px solid var(--rf-border-color, #121212); }
    .banner-fumble { background: var(--rf-color-red, #e63946); color: #fff; font-weight: 900; font-size: 0.82rem; text-align: center; padding: 5px; margin: -14px -14px 10px -14px; }
    .confetti-particles { position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; }
    .confetti-piece { position: absolute; width: 7px; height: 7px; animation: confetti-fall 1.4s ease-out infinite; }
    .confetti-piece:nth-child(1) { left: 15%; background: var(--rf-color-red); animation-delay: 0s; }
    .confetti-piece:nth-child(2) { left: 35%; background: var(--rf-color-blue); animation-delay: 0.2s; }
    .confetti-piece:nth-child(3) { left: 55%; background: var(--rf-color-yellow); animation-delay: 0.1s; }
    .confetti-piece:nth-child(4) { left: 75%; background: #121212; animation-delay: 0.3s; }
    .confetti-piece:nth-child(5) { left: 90%; background: var(--rf-color-red); animation-delay: 0.15s; }
    @keyframes confetti-fall { 0% { transform: translateY(-10px) rotate(0deg); opacity: 1; } 100% { transform: translateY(110px) rotate(360deg); opacity: 0; } }
    .result-score-display { display: flex; align-items: baseline; justify-content: center; gap: 10px; margin: 8px 0; }
    .score-total { font-size: 3.2rem; font-weight: 900; line-height: 1; }
    .score-label { font-size: 0.9rem; font-weight: 800; text-transform: uppercase; color: var(--rf-text-muted, #4b5563); }
    .result-breakdown { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; font-size: 0.82rem; font-weight: 700; padding-top: 8px; border-top: 1px solid #ddd; }
    .roll-item { display: inline-flex; align-items: center; justify-content: center; min-width: 22px; height: 22px; padding: 0 3px; border: 1px solid #121212; background: #ffffff; font-weight: 800; }
    .roll-item.dropped { opacity: 0.4; text-decoration: line-through; background: #eee; }
    .roll-item.crit { background: var(--rf-color-yellow, #ffb703); }
    .roll-item.fumble { background: var(--rf-color-red, #e63946); color: #fff; }
    .error-text { color: var(--rf-color-red, #e63946); font-size: 0.8rem; font-weight: 700; }
  `;

  connectedCallback() {
    super.connectedCallback();
    if (this.formula) this.formulaInput = this.formula;
    if (this.forcedResult) this.lastResult = this.forcedResult;
  }

  willUpdate(changedProps: Map<string, unknown>) {
    if (changedProps.has('forcedResult') && this.forcedResult) this.lastResult = this.forcedResult;
    if (changedProps.has('formula') && this.formula) this.formulaInput = this.formula;
  }

  private handleSelectDie(sides: number) {
    this.selectedSides = sides;
    this.updateFormulaForCurrentMode();
  }

  private handleSelectMode(mode: RollMode) {
    this.mode = mode;
    this.updateFormulaForCurrentMode();
  }

  private updateFormulaForCurrentMode() {
    const currentModMatch = this.formulaInput.match(/([+-]\s*\d+)$/);
    const modStr = currentModMatch ? currentModMatch[1].replace(/\s+/g, '') : '';
    if (this.mode === 'advantage') {
      this.formulaInput = `2d${this.selectedSides}kh1${modStr}`;
    } else if (this.mode === 'disadvantage') {
      this.formulaInput = `2d${this.selectedSides}kl1${modStr}`;
    } else {
      this.formulaInput = `1d${this.selectedSides}${modStr}`;
    }
  }

  public roll(): DiceRollResult | null {
    this.errorMessage = '';
    try {
      this.isRolling = true;
      const result = parseAndRoll(this.formulaInput);
      setTimeout(() => {
        this.isRolling = false;
        this.lastResult = result;
        this.dispatchEvent(
          new CustomEvent('dice-rolled', {
            detail: {
              sessionId: this.sessionId,
              rollerId: this.rollerId,
              rollerName: this.rollerName,
              formula: result.formula,
              total: result.total,
              rolls: result.rolls,
              keptRolls: result.keptRolls,
              isCrit: result.isCrit,
              isFumble: result.isFumble,
              is_crit: result.isCrit,
              is_fumble: result.isFumble,
            },
            bubbles: true,
            composed: true,
          })
        );
      }, 300);
      return result;
    } catch (err: unknown) {
      this.isRolling = false;
      this.errorMessage = err instanceof Error ? err.message : String(err);
      return null;
    }
  }

  render() {
    const res = this.lastResult;
    return html`
      <div class="roller-card">
        <div class="card-header">
          <h2><span class="badge-icon">🎲</span> Bauhaus Geometric Dice Roller</h2>
          <span class="section-label">${this.rollerName}</span>
        </div>

        <div class="section-label">Polyhedral Geometry</div>
        <div class="dice-chips-grid">
          ${DICE_OPTIONS.map(
            (d) => html`
              <button
                class="dice-chip ${this.selectedSides === d.sides ? 'active' : ''}"
                @click=${() => this.handleSelectDie(d.sides)}
              >
                <span>${d.symbol}</span>
                <span>${d.label}</span>
              </button>
            `
          )}
        </div>

        <div class="section-label">Roll Stance</div>
        <div class="mode-toggles">
          <button
            class="mode-btn ${this.mode === 'advantage' ? 'active' : ''}"
            data-mode="advantage"
            @click=${() => this.handleSelectMode('advantage')}
          >
            Advantage (+d20 kh1)
          </button>
          <button
            class="mode-btn ${this.mode === 'normal' ? 'active' : ''}"
            data-mode="normal"
            @click=${() => this.handleSelectMode('normal')}
          >
            Normal
          </button>
          <button
            class="mode-btn ${this.mode === 'disadvantage' ? 'active' : ''}"
            data-mode="disadvantage"
            @click=${() => this.handleSelectMode('disadvantage')}
          >
            Disadvantage (+d20 kl1)
          </button>
        </div>

        <div class="section-label">Formula & Execution</div>
        <div class="formula-row">
          <input
            type="text"
            class="formula-input"
            .value=${this.formulaInput}
            @input=${(e: Event) => {
              this.formulaInput = (e.target as HTMLInputElement).value;
              this.errorMessage = '';
            }}
            aria-label="Dice roll formula"
            placeholder="e.g. 1d20+5, 8d6+4"
          />
          <button
            class="roll-action-btn ${this.isRolling ? 'rolling' : ''}"
            @click=${() => this.roll()}
            ?disabled=${this.isRolling}
          >
            ${this.isRolling
              ? html`<span class="tumble-animation">🎲</span> Rolling...`
              : html`<span>🎲</span> ROLL`}
          </button>
        </div>

        ${this.errorMessage ? html`<div class="error-text">${this.errorMessage}</div>` : ''}

        ${res
          ? html`
              <div
                class="result-container ${res.isCrit ? 'crit' : ''} ${res.isFumble ? 'fumble' : ''}"
              >
                ${res.isCrit
                  ? html`
                      <div class="banner-crit">★ CRITICAL HIT! NATURAL 20 ★</div>
                      <div class="confetti-particles">
                        <div class="confetti-piece"></div>
                        <div class="confetti-piece"></div>
                        <div class="confetti-piece"></div>
                        <div class="confetti-piece"></div>
                        <div class="confetti-piece"></div>
                      </div>
                    `
                  : ''}
                ${res.isFumble
                  ? html`<div class="banner-fumble">⚠ CRITICAL FUMBLE! NATURAL 1 ⚠</div>`
                  : ''}

                <div class="result-score-display">
                  <span class="score-total">${res.total}</span>
                  <span class="score-label">Total Result</span>
                </div>

                <div class="result-breakdown">
                  <span><strong>Formula:</strong> ${res.formula || this.formulaInput}</span>
                  <span>
                    <strong>Rolls:</strong>
                    ${(() => {
                      const remainingKept = [...res.keptRolls];
                      return res.rolls.map((r) => {
                        const keptIdx = remainingKept.indexOf(r);
                        const isKept = keptIdx !== -1;
                        if (isKept) remainingKept.splice(keptIdx, 1);
                        const isCritDie = res.sides === 20 && r === 20 && isKept;
                        const isFumbleDie = res.sides === 20 && r === 1 && isKept;
                        return html`
                          <span
                            class="roll-item ${!isKept ? 'dropped' : ''} ${isCritDie
                              ? 'crit'
                              : ''} ${isFumbleDie ? 'fumble' : ''}"
                          >
                            ${r}
                          </span>
                        `;
                      });
                    })()}
                  </span>
                  ${res.modifier !== 0
                    ? html`<span><strong>Mod:</strong> ${res.modifier > 0 ? `+${res.modifier}` : res.modifier}</span>`
                    : ''}
                </div>
              </div>
            `
          : ''}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-dice-roller': RunefobleDiceRoller;
  }
}
