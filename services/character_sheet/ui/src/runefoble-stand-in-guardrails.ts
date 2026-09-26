import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('runefoble-stand-in-guardrails')
export class RunefobleStandInGuardrails extends LitElement {
  @property({ type: String }) characterId = '';
  @property({ type: String }) characterName = '';
  @property({ type: Object }) preserveSpellSlots: Record<number, number> = { 3: 1 };
  @property({ type: Array }) protectAllies: string[] = ['Marcus'];
  @property({ type: Number }) protectAllyHpThreshold = 0.3;
  @property({ type: String }) riskThreshold: 'cautious' | 'balanced' | 'reckless' = 'cautious';
  @property({ type: Boolean }) avoidMelee = true;
  @property({ type: Boolean }) permadeathSafeguard = true;
  @property({ type: Array }) customPriorities: string[] = [
    'Save Level 3 slots for Revivify',
    'Prioritize healing Marcus if under 30% HP',
    'Avoid frontline melee',
  ];

  @state() private newAllyInput = '';
  @state() private saveStatus = '';

  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      background: var(--rf-bg-card, #1e1e24);
      border: var(--rf-border-width, 1px) solid var(--rf-border-color, #2d2d39);
      border-radius: var(--rf-border-radius, 8px);
      padding: 24px;
      color: var(--rf-text-primary, #f3f4f6);
      max-width: 580px;
      box-sizing: border-box;
      box-shadow: var(--rf-shadow, 0 4px 6px -1px rgba(0, 0, 0, 0.3));
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      border-bottom: 1px solid var(--rf-border-subtle, #374151);
      padding-bottom: 12px;
    }
    .header h3 {
      margin: 0;
      font-size: 1.25rem;
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--rf-text-primary, #f3f4f6);
    }
    .subtext {
      font-size: 0.85rem;
      color: var(--rf-text-muted, #9ca3af);
      margin-top: 4px;
    }
    .section {
      margin-bottom: 16px;
      background: var(--rf-bg-inset, #131317);
      border: 1px solid var(--rf-border-subtle, #374151);
      border-radius: 8px;
      padding: 14px;
    }
    .section-title {
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-weight: 700;
      color: var(--rf-accent-secondary, #60a5fa);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .toggle-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .toggle-row:last-child {
      border-bottom: none;
    }
    .toggle-label {
      font-size: 0.9rem;
      font-weight: 500;
    }
    .toggle-desc {
      font-size: 0.75rem;
      color: var(--rf-text-muted, #9ca3af);
    }
    input[type='checkbox'] {
      width: 18px;
      height: 18px;
      cursor: pointer;
      accent-color: var(--rf-accent-secondary, #3b82f6);
    }
    .chips-container {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 8px;
    }
    .chip {
      background: var(--rf-accent-tertiary, #f59e0b);
      color: #111827;
      font-weight: 600;
      font-size: 0.8rem;
      padding: 3px 10px;
      border-radius: 9999px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .chip-remove {
      cursor: pointer;
      font-weight: bold;
    }
    .input-row {
      display: flex;
      gap: 8px;
      margin-top: 8px;
    }
    input[type='text'], select {
      flex: 1;
      background: var(--rf-bg-card, #1e1e24);
      border: 1px solid var(--rf-border-subtle, #374151);
      border-radius: 6px;
      color: var(--rf-text-primary, #f3f4f6);
      padding: 6px 10px;
      font-size: 0.85rem;
    }
    .btn {
      background: var(--rf-accent-secondary, #3b82f6);
      color: var(--rf-text-inverse, #ffffff);
      border: none;
      border-radius: 6px;
      padding: 8px 14px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s;
    }
    .btn:hover {
      opacity: 0.9;
    }
    .btn-secondary {
      background: var(--rf-bg-inset, #2b2b36);
      border: 1px solid var(--rf-border-subtle, #374151);
      color: var(--rf-text-primary, #f3f4f6);
    }
    .btn-takeover {
      background: var(--rf-accent-primary, #10b981);
    }
    .actions-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 20px;
    }
    .status-msg {
      font-size: 0.8rem;
      color: var(--rf-accent-primary, #10b981);
    }
  `;

  private addAlly() {
    if (this.newAllyInput.trim()) {
      this.protectAllies = [...this.protectAllies, this.newAllyInput.trim()];
      this.newAllyInput = '';
    }
  }

  private removeAlly(index: number) {
    this.protectAllies = this.protectAllies.filter((_, i) => i !== index);
  }

  private handleSave() {
    const detail = {
      characterId: this.characterId,
      preserve_spell_slots: this.preserveSpellSlots,
      protect_allies: this.protectAllies,
      protect_ally_hp_threshold: this.protectAllyHpThreshold,
      risk_threshold: this.riskThreshold,
      avoid_melee: this.avoidMelee,
      permadeath_safeguard: this.permadeathSafeguard,
      custom_priorities: this.customPriorities,
    };
    this.dispatchEvent(
      new CustomEvent('guardrails-saved', {
        detail,
        bubbles: true,
        composed: true,
      })
    );
    this.saveStatus = 'Tactical Guardrails Saved!';
    setTimeout(() => {
      this.saveStatus = '';
    }, 3000);
  }

  private handleHotSwap() {
    this.dispatchEvent(
      new CustomEvent('hot-swap-requested', {
        detail: { characterId: this.characterId },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    return html`
      <div class="header">
        <div>
          <h3>🛡️ Stand-In Tactical Guardrails</h3>
          <div class="subtext">
            Playstyle constraints & zero-HP permadeath protection for
            <strong>${this.characterName || 'Hero'}</strong>
          </div>
        </div>
        <button class="btn btn-takeover" @click=${this.handleHotSwap}>
          ⚡ Take Control (Hot-Swap)
        </button>
      </div>

      <div class="section">
        <div class="section-title">✨ Spell Slot Preservation</div>
        <div class="toggle-row">
          <div>
            <div class="toggle-label">Reserve Level 3 Slots (Revivify)</div>
            <div class="toggle-desc">Stand-in will not cast level 3 spells unless explicitly ordered</div>
          </div>
          <input
            type="checkbox"
            .checked=${Boolean(this.preserveSpellSlots[3])}
            @change=${(e: Event) => {
              const target = e.target as HTMLInputElement;
              const slots = { ...this.preserveSpellSlots };
              if (target.checked) slots[3] = 1;
              else delete slots[3];
              this.preserveSpellSlots = slots;
            }}
          />
        </div>
      </div>

      <div class="section">
        <div class="section-title">🤝 Party Member Protection Affinities</div>
        <div class="chips-container">
          ${this.protectAllies.map(
            (ally, idx) => html`
              <span class="chip">
                <span>🛡️ ${ally}</span>
                <span class="chip-remove" @click=${() => this.removeAlly(idx)}>×</span>
              </span>
            `
          )}
        </div>
        <div class="input-row">
          <input
            type="text"
            placeholder="Add ally name (e.g. Marcus)"
            .value=${this.newAllyInput}
            @input=${(e: Event) => (this.newAllyInput = (e.target as HTMLInputElement).value)}
            @keydown=${(e: KeyboardEvent) => e.key === 'Enter' && this.addAlly()}
          />
          <button class="btn btn-secondary" @click=${this.addAlly}>Add</button>
        </div>
      </div>

      <div class="section">
        <div class="section-title">⚠️ Tactical Posture & Risk Thresholds</div>
        <div class="toggle-row">
          <div>
            <div class="toggle-label">Avoid Frontline Melee</div>
            <div class="toggle-desc">Maintain safe tactical distance; favor ranged attacks and spells</div>
          </div>
          <input
            type="checkbox"
            .checked=${this.avoidMelee}
            @change=${(e: Event) => (this.avoidMelee = (e.target as HTMLInputElement).checked)}
          />
        </div>
        <div class="toggle-row">
          <div>
            <div class="toggle-label">Permadeath Safeguard (Zero-HP Stabilization)</div>
            <div class="toggle-desc">Automatically stabilize at 0 HP without death save failures</div>
          </div>
          <input
            type="checkbox"
            .checked=${this.permadeathSafeguard}
            @change=${(e: Event) => (this.permadeathSafeguard = (e.target as HTMLInputElement).checked)}
          />
        </div>
      </div>

      <div class="actions-bar">
        <span class="status-msg">${this.saveStatus}</span>
        <button class="btn" @click=${this.handleSave}>Save Tactical Guardrails</button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-stand-in-guardrails': RunefobleStandInGuardrails;
  }
}
