import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { characterBuilderModalStyles } from './runefoble-character-builder-modal.styles.ts';
import {
  type AbilityScores,
  type CreateCharacterPayload,
  formatModifier,
} from './types.ts';

const DEFAULT_ABILITIES: AbilityScores = { str: 15, dex: 14, con: 13, int: 12, wis: 10, cha: 8 };

const PORTRAIT_PRESETS = [
  { id: 'fighter', label: 'Fighter', url: '/assets/portraits/fighter.svg' },
  { id: 'cleric', label: 'Cleric', url: '/assets/portraits/cleric.svg' },
  { id: 'wizard', label: 'Wizard', url: '/assets/portraits/wizard.svg' },
  { id: 'rogue', label: 'Rogue', url: '/assets/portraits/rogue.svg' },
  { id: 'paladin', label: 'Paladin', url: '/assets/portraits/paladin.svg' },
];

const STANDARD_CLASSES = [
  'Fighter', 'Wizard', 'Cleric', 'Rogue', 'Paladin', 'Barbarian',
  'Bard', 'Druid', 'Monk', 'Ranger', 'Sorcerer', 'Warlock',
];

@customElement('runefoble-character-builder-modal')
export class RunefobleCharacterBuilderModal extends LitElement {
  static styles = [characterBuilderModalStyles];

  @property({ type: Boolean }) open = false;
  @property({ type: Object }) initialData?: Partial<CreateCharacterPayload>;

  @state() private name = '';
  @state() private characterClass = 'Fighter';
  @state() private subclass = '';
  @state() private level = 1;
  @state() private maxHp = 12;
  @state() private armorClass = 16;
  @state() private speed = 30;
  @state() private abilityScores: AbilityScores = { ...DEFAULT_ABILITIES };
  @state() private portraitUrl = PORTRAIT_PRESETS[0].url;
  @state() private errorMessage = '';

  willUpdate(changed: Map<string, unknown>) {
    if (changed.has('open') && this.open && this.initialData) {
      const d = this.initialData;
      if (d.name !== undefined) this.name = d.name;
      if (d.characterClass) this.characterClass = d.characterClass;
      if (d.subclass !== undefined) this.subclass = d.subclass;
      if (d.level) this.level = d.level;
      if (d.maxHp) this.maxHp = d.maxHp;
      if (d.armorClass) this.armorClass = d.armorClass;
      if (d.speed) this.speed = d.speed;
      if (d.abilityScores) this.abilityScores = { ...d.abilityScores };
      if (d.portraitUrl) this.portraitUrl = d.portraitUrl;
    }
  }

  private handleScoreChange(key: keyof AbilityScores, value: number) {
    const clamped = Math.max(1, Math.min(30, Number(value) || 10));
    this.abilityScores = { ...this.abilityScores, [key]: clamped };
  }

  private handleSubmit(e: Event) {
    e.preventDefault();
    if (!this.name.trim()) {
      this.errorMessage = 'Character name is required.';
      return;
    }
    if (this.maxHp <= 0 || this.level < 1) {
      this.errorMessage = 'Invalid HP or Level.';
      return;
    }

    const payload: CreateCharacterPayload = {
      name: this.name.trim(),
      characterClass: this.characterClass,
      subclass: this.subclass.trim() || undefined,
      level: Number(this.level),
      maxHp: Number(this.maxHp),
      armorClass: Number(this.armorClass),
      speed: Number(this.speed),
      abilityScores: { ...this.abilityScores },
      portraitUrl: this.portraitUrl,
    };

    this.dispatchEvent(new CustomEvent<CreateCharacterPayload>('create-character', {
      detail: payload,
      bubbles: true,
      composed: true,
    }));
    this.closeModal();
  }

  private closeModal() {
    this.errorMessage = '';
    this.dispatchEvent(new CustomEvent('builder-close', { bubbles: true, composed: true }));
  }

  private renderAbilities() {
    const keys: (keyof AbilityScores)[] = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
    return html`
      <div class="ability-grid">
        ${keys.map((k) => html`
          <div class="ability-box">
            <span class="ability-label">${k}</span>
            <input type="number" class="ability-input" aria-label="${k.toUpperCase()} score"
              .value=${String(this.abilityScores[k])}
              @input=${(e: Event) => this.handleScoreChange(k, Number((e.target as HTMLInputElement).value))} />
            <span class="ability-mod">${formatModifier(this.abilityScores[k])}</span>
          </div>
        `)}
      </div>
    `;
  }

  render() {
    if (!this.open) return html``;

    return html`
      <div class="modal-backdrop" @click=${(e: MouseEvent) => { if (e.target === e.currentTarget) this.closeModal(); }}>
        <div class="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="builder-title">
          <header class="modal-header">
            <h2 id="builder-title" class="modal-title">Create Character</h2>
            <button class="close-btn" aria-label="Close modal" @click=${this.closeModal}>×</button>
          </header>

          <form @submit=${this.handleSubmit} class="modal-body">
            ${this.errorMessage ? html`<div class="error-banner">${this.errorMessage}</div>` : ''}

            <div class="form-group">
              <label for="char-name">Character Name *</label>
              <input id="char-name" class="form-input" type="text" required placeholder="e.g. Valeros of Korvosa"
                .value=${this.name} @input=${(e: Event) => { this.name = (e.target as HTMLInputElement).value; }} />
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="char-class">Class</label>
                <select id="char-class" class="form-select" .value=${this.characterClass}
                  @change=${(e: Event) => { this.characterClass = (e.target as HTMLSelectElement).value; }}>
                  ${STANDARD_CLASSES.map((cls) => html`<option value=${cls}>${cls}</option>`)}
                </select>
              </div>
              <div class="form-group">
                <label for="char-subclass">Subclass (Optional)</label>
                <input id="char-subclass" class="form-input" type="text" placeholder="e.g. Battle Master"
                  .value=${this.subclass} @input=${(e: Event) => { this.subclass = (e.target as HTMLInputElement).value; }} />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="char-level">Level</label>
                <input id="char-level" class="form-input" type="number" min="1" max="20" .value=${String(this.level)}
                  @input=${(e: Event) => { this.level = Number((e.target as HTMLInputElement).value); }} />
              </div>
              <div class="form-group">
                <label for="char-hp">Max HP</label>
                <input id="char-hp" class="form-input" type="number" min="1" .value=${String(this.maxHp)}
                  @input=${(e: Event) => { this.maxHp = Number((e.target as HTMLInputElement).value); }} />
              </div>
              <div class="form-group">
                <label for="char-ac">Armor Class</label>
                <input id="char-ac" class="form-input" type="number" min="1" .value=${String(this.armorClass)}
                  @input=${(e: Event) => { this.armorClass = Number((e.target as HTMLInputElement).value); }} />
              </div>
              <div class="form-group">
                <label for="char-speed">Speed (ft)</label>
                <input id="char-speed" class="form-input" type="number" min="5" step="5" .value=${String(this.speed)}
                  @input=${(e: Event) => { this.speed = Number((e.target as HTMLInputElement).value); }} />
              </div>
            </div>

            <div class="form-group">
              <label>Ability Scores</label>
              ${this.renderAbilities()}
            </div>

            <div class="form-group">
              <label>Token Portrait</label>
              <div class="portrait-options">
                ${PORTRAIT_PRESETS.map((p) => html`
                  <button type="button" class="portrait-btn ${this.portraitUrl === p.url ? 'selected' : ''}"
                    title=${p.label} @click=${() => { this.portraitUrl = p.url; }}>
                    <img src=${p.url} alt=${p.label} />
                  </button>
                `)}
              </div>
            </div>

            <footer class="modal-footer">
              <button type="button" class="btn btn-cancel" @click=${this.closeModal}>Cancel</button>
              <button type="submit" class="btn btn-submit">Create Character</button>
            </footer>
          </form>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-character-builder-modal': RunefobleCharacterBuilderModal;
  }
}
