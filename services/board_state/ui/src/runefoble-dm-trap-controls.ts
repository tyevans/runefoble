import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { dmTrapControlsStyles } from './runefoble-dm-trap-controls.styles.ts';

export interface TrapTypeOption {
  id: string;
  name: string;
  icon: string;
  triggerType: 'step' | 'touch' | 'proximity';
  proximityRadius: number;
  damageDice: string;
  dcDetection: number;
}

const TRAP_PRESETS: TrapTypeOption[] = [
  { id: 'pit_trap', name: 'Spike Pit', icon: '🕳️', triggerType: 'step', proximityRadius: 1, damageDice: '2d10', dcDetection: 15 },
  { id: 'glyph', name: 'Glyph of Warding', icon: '✨', triggerType: 'proximity', proximityRadius: 2, damageDice: '5d8', dcDetection: 16 },
  { id: 'tripwire', name: 'Tripwire', icon: '🕸️', triggerType: 'touch', proximityRadius: 1, damageDice: '1d6', dcDetection: 12 },
];

@customElement('runefoble-dm-trap-controls')
export class RunefobleDmTrapControls extends LitElement {
  static styles = dmTrapControlsStyles;

  @property({ type: Boolean }) layerVisible = true;
  @property({ type: String }) selectedTrapType = 'pit_trap';
  @property({ type: String }) triggerType: 'step' | 'touch' | 'proximity' = 'step';
  @property({ type: Number }) proximityRadius = 1;
  @property({ type: String }) damageDice = '2d10';
  @property({ type: Number }) dcDetection = 15;
  @property({ type: Boolean }) isSecret = true;
  @state() private statusMessage = '';

  selectPreset(preset: TrapTypeOption) {
    this.selectedTrapType = preset.id;
    this.triggerType = preset.triggerType;
    this.proximityRadius = preset.proximityRadius;
    this.damageDice = preset.damageDice;
    this.dcDetection = preset.dcDetection;
    this.dispatchEvent(new CustomEvent('trap-selected', { bubbles: true, composed: true, detail: preset }));
  }

  toggleLayer() {
    this.layerVisible = !this.layerVisible;
    this.dispatchEvent(new CustomEvent('layer-toggled', { bubbles: true, composed: true, detail: { layerVisible: this.layerVisible } }));
  }

  armTrap() {
    const detail = {
      trapType: this.selectedTrapType,
      triggerType: this.triggerType,
      proximityRadius: this.proximityRadius,
      damageDice: this.damageDice,
      dcDetection: this.dcDetection,
      isSecret: this.isSecret,
    };
    this.statusMessage = `Armed ${this.selectedTrapType}!`;
    this.dispatchEvent(new CustomEvent('trap-armed', { bubbles: true, composed: true, detail }));
    this.dispatchEvent(new CustomEvent('trap-placed', { bubbles: true, composed: true, detail }));
  }

  openMapSwitcher() {
    this.dispatchEvent(new CustomEvent('open-map-switcher', { bubbles: true, composed: true }));
  }

  render() {
    return html`
      <div class="hud-header">
        <div class="title"><span>🛡️ Hidden Layer</span><span class="dm-badge">DM Only</span></div>
        <button class="btn-hud" @click="${this.toggleLayer}">
          ${this.layerVisible ? '👁️ Visible' : '🙈 Hidden'}
        </button>
      </div>

      <div class="trap-palette">
        ${TRAP_PRESETS.map((p) => html`
          <button class="trap-btn ${this.selectedTrapType === p.id ? 'active' : ''}" @click="${() => this.selectPreset(p)}">
            <span>${p.icon}</span><span>${p.name}</span>
          </button>
        `)}
      </div>

      <div class="controls-row">
        <label>Trigger:
          <select .value="${this.triggerType}" @change="${(e: Event) => this.triggerType = (e.target as HTMLSelectElement).value as any}">
            <option value="step">Step</option><option value="touch">Touch</option><option value="proximity">Proximity</option>
          </select>
        </label>
        <label>Radius:
          <input type="number" min="1" max="5" .value="${String(this.proximityRadius)}"
            @input="${(e: Event) => this.proximityRadius = Number((e.target as HTMLInputElement).value)}" />
        </label>
        <label>DC:
          <input type="number" min="5" max="30" .value="${String(this.dcDetection)}"
            @input="${(e: Event) => this.dcDetection = Number((e.target as HTMLInputElement).value)}" />
        </label>
      </div>

      <div class="danger-zone-preview">
        <span><span class="danger-pulse"></span> Danger Zone: ${this.proximityRadius * 5}ft (${this.triggerType})</span>
        <span>DC ${this.dcDetection} | ${this.damageDice}</span>
      </div>
      ${this.statusMessage ? html`<div style="font-size: 0.75rem; font-weight: 700; color: #2a9d8f; margin-bottom: 6px;">${this.statusMessage}</div>` : ''}

      <div class="action-footer">
        <button class="btn-hud primary" @click="${this.armTrap}">⚔️ Arm Cell</button>
        <button class="btn-hud accent" @click="${this.openMapSwitcher}">🗺️ Switch Map</button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-dm-trap-controls': RunefobleDmTrapControls;
  }
}
