import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { settingsModalStyles } from '../runefoble-settings-modal.styles.ts';

@customElement('runefoble-settings-dice')
export class RunefobleSettingsDice extends LitElement {
  static styles = settingsModalStyles;

  @property({ type: Boolean }) dicePhysics: boolean = true;
  @property({ type: Boolean }) diceSound: boolean = true;
  @state() private lastRoll: number | null = null;

  private handlePhysicsChange(e: Event): void {
    const checked = (e.target as HTMLInputElement).checked;
    this.dicePhysics = checked;
    this.dispatchEvent(
      new CustomEvent('dice-physics-change', {
        detail: { dicePhysics: checked },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleSoundChange(e: Event): void {
    const checked = (e.target as HTMLInputElement).checked;
    this.diceSound = checked;
    this.dispatchEvent(
      new CustomEvent('dice-sound-change', {
        detail: { diceSound: checked },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleTestRoll(): void {
    const roll = Math.floor(Math.random() * 20) + 1;
    this.lastRoll = roll;
    this.dispatchEvent(
      new CustomEvent('dice-test-roll', {
        detail: { roll },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    return html`
      <div class="form-group">
        <label class="checkbox-row">
          <input
            type="checkbox"
            .checked=${this.dicePhysics}
            @change=${this.handlePhysicsChange}
          />
          Enable 3D Kinetic Dice Physics Simulation
        </label>
      </div>

      <div class="form-group">
        <label class="checkbox-row">
          <input
            type="checkbox"
            .checked=${this.diceSound}
            @change=${this.handleSoundChange}
          />
          Dice Rolling Spatial Foley Audio
        </label>
      </div>

      <div class="form-group" style="margin-top: 8px;">
        <button
          type="button"
          class="test-roll-btn"
          @click=${this.handleTestRoll}
          style="padding: 8px 14px; font-size: 0.85rem; font-weight: 700; background: var(--rf-bg-surface); color: var(--rf-text-primary); border: var(--rf-border-width, 2px) solid var(--rf-border-color); cursor: pointer; align-self: flex-start;"
        >
          🎲 Roll Test Die (d20)
        </button>
        ${this.lastRoll !== null
          ? html`<span class="roll-result" style="font-size: 0.85rem; font-weight: 700; margin-top: 6px;">Result: <strong>${this.lastRoll}</strong></span>`
          : ''}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-settings-dice': RunefobleSettingsDice;
  }
}
