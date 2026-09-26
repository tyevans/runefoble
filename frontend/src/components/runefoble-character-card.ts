import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

export interface CharacterCondition {
  id: string;
  name: string;
  severity?: 'minor' | 'moderate' | 'severe';
  source: 'session_penalty' | 'spell' | 'environment';
  description: string;
}

@customElement('runefoble-character-card')
export class RunefobleCharacterCard extends LitElement {
  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      background: var(--rf-bg-card, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      padding: 16px;
      color: var(--rf-text-primary, #121212);
      width: 320px;
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      box-sizing: border-box;
      transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
      border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      padding-bottom: 8px;
    }
    .name-title {
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--rf-text-primary, #121212);
    }
    .class-level {
      font-size: 0.85rem;
      color: var(--rf-text-muted, #4b5563);
      font-weight: 600;
    }
    .ai-badge {
      background: var(--rf-accent-tertiary, #ffb703);
      color: var(--rf-color-dark, #121212);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      font-size: 0.7rem;
      padding: 2px 8px;
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      font-weight: 700;
    }
    .hp-container {
      margin-bottom: 12px;
    }
    .hp-header {
      display: flex;
      justify-content: space-between;
      font-size: 0.8rem;
      margin-bottom: 4px;
      font-weight: 700;
      color: var(--rf-text-primary, #121212);
    }
    .hp-bar-bg {
      height: 10px;
      background: var(--rf-bg-canvas, #f8f9fa);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      overflow: hidden;
    }
    .hp-bar-fill {
      height: 100%;
      background: var(--rf-accent-secondary, #1d3557);
      transition: width 0.3s ease;
    }
    .hp-bar-fill.low {
      background: var(--rf-accent-primary, #e63946);
    }
    .conditions-container {
      margin-top: 12px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .condition-tag {
      font-size: 0.72rem;
      padding: 3px 8px;
      border-radius: var(--rf-border-radius, 0px);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-weight: 600;
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    }
    .condition-penalty {
      background: var(--rf-accent-tertiary, #ffb703);
      color: var(--rf-color-dark, #121212);
    }
    .condition-normal {
      background: var(--rf-accent-secondary, #1d3557);
      color: var(--rf-color-light, #ffffff);
    }
    .stats-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-top: 12px;
      text-align: center;
      background: var(--rf-bg-canvas, #f8f9fa);
      padding: 8px;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    }
    .stat-label {
      font-size: 0.7rem;
      color: var(--rf-text-muted, #4b5563);
      text-transform: uppercase;
      font-weight: 700;
    }
    .stat-value {
      font-size: 1.05rem;
      font-weight: 800;
      color: var(--rf-text-primary, #121212);
    }
  `;

  @property({ type: String }) characterName = 'Valeros the Bold';
  @property({ type: String }) characterClass = 'Fighter 4';
  @property({ type: Boolean }) isAiStandIn = false;
  @property({ type: Number }) currentHp = 34;
  @property({ type: Number }) maxHp = 42;
  @property({ type: Number }) armorClass = 18;
  @property({ type: Number }) initiative = 2;
  @property({ type: Number }) speed = 30;
  @property({ type: Array }) conditions: CharacterCondition[] = [];

  render() {
    const hpPercent = Math.max(0, Math.min(100, (this.currentHp / this.maxHp) * 100));
    const isLowHp = hpPercent < 30;

    return html`
      <div class="card-header">
        <div>
          <div class="name-title">${this.characterName}</div>
          <div class="class-level">${this.characterClass}</div>
        </div>
        ${this.isAiStandIn
          ? html`<span class="ai-badge">🤖 AI Stand-in</span>`
          : html``}
      </div>

      <div class="hp-container">
        <div class="hp-header">
          <span>Hit Points</span>
          <span>${this.currentHp} / ${this.maxHp}</span>
        </div>
        <div class="hp-bar-bg">
          <div
            class="hp-bar-fill ${isLowHp ? 'low' : ''}"
            style="width: ${hpPercent}%"
          ></div>
        </div>
      </div>

      <div class="stats-row">
        <div>
          <div class="stat-label">AC</div>
          <div class="stat-value">${this.armorClass}</div>
        </div>
        <div>
          <div class="stat-label">Init</div>
          <div class="stat-value">+${this.initiative}</div>
        </div>
        <div>
          <div class="stat-label">Speed</div>
          <div class="stat-value">${this.speed}ft</div>
        </div>
      </div>

      ${this.conditions.length > 0
        ? html`
            <div class="conditions-container">
              ${this.conditions.map(
                (c) => html`
                  <span
                    class="condition-tag ${c.source === 'session_penalty' ? 'condition-penalty' : 'condition-normal'}"
                    title="${c.description}"
                  >
                    ${c.source === 'session_penalty' ? '🍺' : '✨'} ${c.name}
                  </span>
                `
              )}
            </div>
          `
        : html``}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-character-card': RunefobleCharacterCard;
  }
}
