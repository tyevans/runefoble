import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { reactionPromptStyles } from './runefoble-combat-reaction-prompt.styles.ts';

@customElement('runefoble-ready-action-card')
export class RunefobleReadyActionCard extends LitElement {
  static styles = [reactionPromptStyles];

  @property({ type: String }) sessionId = '';
  @property({ type: String }) combatantId = '';
  @property({ type: String }) combatantName = 'Combatant';
  @property({ type: String }) triggerType = 'enemy_enters_range';
  @property({ type: String }) triggerCondition = '';
  @property({ type: String }) readiedAction = '';
  @property({ type: String }) targetId = '';
  @property({ type: Number }) rangeCells = 6;
  @property({ type: Boolean }) isArmed = false;

  armAction(): void {
    if (!this.readiedAction) return;
    this.isArmed = true;
    this.dispatchEvent(new CustomEvent('ready-action-registered', {
      detail: {
        sessionId: this.sessionId, combatantId: this.combatantId, combatantName: this.combatantName,
        triggerType: this.triggerType, triggerCondition: this.triggerCondition,
        readiedAction: this.readiedAction, targetId: this.targetId, rangeCells: this.rangeCells,
      },
      bubbles: true, composed: true,
    }));
  }

  disarmAction(): void {
    this.isArmed = false;
    this.dispatchEvent(new CustomEvent('ready-action-cancelled', {
      detail: { sessionId: this.sessionId, combatantId: this.combatantId },
      bubbles: true, composed: true,
    }));
  }

  render() {
    return html`
      <div class="ready-card">
        <div class="urgent-header">
          <h3 class="urgent-title">🎯 Ready-Action Trigger</h3>
          <span class="status-badge ${this.isArmed ? 'resolved' : 'expired'}">${this.isArmed ? 'ARMED' : 'STANDBY'}</span>
        </div>
        ${this.isArmed ? html`
          <div class="trigger-banner">
            <div><strong>Condition:</strong> ${this.triggerCondition || this.triggerType}</div>
            <div style="margin-top: 4px;"><strong>Action:</strong> ${this.readiedAction} (Range: ${this.rangeCells} cells)</div>
          </div>
          <button class="decline-btn" @click=${this.disarmAction}>Cancel / Disarm Trigger</button>
        ` : html`
          <div class="form-group">
            <label class="form-label" for="cond-input">Condition / Spoken Phrase</label>
            <input id="cond-input" class="form-input" type="text" placeholder="e.g. if the goblin steps into the hallway"
              .value=${this.triggerCondition} @input=${(e: Event) => this.triggerCondition = (e.target as HTMLInputElement).value} />
          </div>
          <div class="form-group">
            <label class="form-label" for="type-select">Trigger Type</label>
            <select id="type-select" class="form-input" .value=${this.triggerType}
              @change=${(e: Event) => this.triggerType = (e.target as HTMLSelectElement).value}>
              <option value="enemy_enters_range">Enemy Enters Range</option>
              <option value="spell_cast">Hostile Spell Cast</option>
              <option value="hostile_attack">Hostile Creature Attacks</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="act-input">Readied Reaction Action</label>
            <input id="act-input" class="form-input" type="text" placeholder="e.g. Shoot Heavy Crossbow"
              .value=${this.readiedAction} @input=${(e: Event) => this.readiedAction = (e.target as HTMLInputElement).value} />
          </div>
          <div class="form-group">
            <label class="form-label" for="range-input">Trigger Range (Grid Cells)</label>
            <input id="range-input" class="form-input" type="number" min="1" max="30"
              .value=${String(this.rangeCells)} @input=${(e: Event) => this.rangeCells = Number((e.target as HTMLInputElement).value) || 6} />
          </div>
          <button class="btn-action primary" style="width: 100%; justify-content: center; margin-top: 8px;"
            @click=${this.armAction}>Arm Ready Action</button>
        `}
      </div>
    `;
  }
}
