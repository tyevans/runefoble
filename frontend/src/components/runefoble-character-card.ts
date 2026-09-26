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
      font-family: system-ui, -apple-system, sans-serif;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 16px;
      color: #f8fafc;
      width: 320px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }
    .name-title {
      font-size: 1.15rem;
      font-weight: 700;
      color: #f1f5f9;
    }
    .class-level {
      font-size: 0.85rem;
      color: #94a3b8;
    }
    .ai-badge {
      background: #831843;
      color: #f472b6;
      border: 1px solid #be185d;
      font-size: 0.7rem;
      padding: 2px 8px;
      border-radius: 9999px;
      font-weight: 600;
    }
    .hp-container {
      margin-bottom: 12px;
    }
    .hp-header {
      display: flex;
      justify-content: space-between;
      font-size: 0.8rem;
      margin-bottom: 4px;
      font-weight: 600;
    }
    .hp-bar-bg {
      height: 8px;
      background: #0f172a;
      border-radius: 4px;
      overflow: hidden;
    }
    .hp-bar-fill {
      height: 100%;
      background: #22c55e;
      transition: width 0.3s ease;
    }
    .hp-bar-fill.low {
      background: #ef4444;
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
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-weight: 500;
    }
    .condition-penalty {
      background: #451a03;
      color: #fb923c;
      border: 1px solid #9a3412;
    }
    .condition-normal {
      background: #172554;
      color: #60a5fa;
      border: 1px solid #1e40af;
    }
    .stats-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-top: 12px;
      text-align: center;
      background: #0f172a;
      padding: 8px;
      border-radius: 8px;
    }
    .stat-label {
      font-size: 0.7rem;
      color: #64748b;
      text-transform: uppercase;
    }
    .stat-value {
      font-size: 1rem;
      font-weight: bold;
      color: #cbd5e1;
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
