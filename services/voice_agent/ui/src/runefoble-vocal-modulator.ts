import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { vocalModulatorStyles } from './runefoble-vocal-modulator.styles.ts';
import type { VocalParams } from './runefoble-vocal-sliders.ts';
import './runefoble-vocal-sliders.ts';

export interface VocalPresetDef {
  id: string;
  name: string;
  key: string;
  icon: string;
  pitchShift: number;
  formantShift: number;
  resonanceHz: number;
  octaveOffset: number;
}

export const VOCAL_PRESETS: VocalPresetDef[] = [
  { id: 'ancient-dragon', name: 'Dragon', key: '1', icon: '🐉', pitchShift: -7.0, formantShift: 0.75, resonanceHz: 140, octaveOffset: -0.5 },
  { id: 'goblin-skulker', name: 'Goblin', key: '2', icon: '👺', pitchShift: 6.5, formantShift: 1.4, resonanceHz: 2800, octaveOffset: 0.5 },
  { id: 'celestial-spirit', name: 'Ethereal', key: '3', icon: '✨', pitchShift: 3.0, formantShift: 1.2, resonanceHz: 1600, octaveOffset: 0.25 },
  { id: 'robotic-construct', name: 'Robotic', key: '4', icon: '🤖', pitchShift: -2.0, formantShift: 0.95, resonanceHz: 440, octaveOffset: 0.0 },
];

@customElement('runefoble-vocal-modulator')
export class RunefobleVocalModulator extends LitElement {
  @property({ type: String }) sessionId = '';
  @property({ type: String }) peerId = 'dm_speaker';
  @property({ type: String }) activePreset: string | null = null;
  @property({ type: Boolean }) isEnabled = false;
  @property({ type: Number }) pitchShift = 0.0;
  @property({ type: Number }) formantShift = 1.0;
  @property({ type: Number }) resonanceHz = 0.0;
  @property({ type: Number }) octaveOffset = 0.0;
  @property({ type: Boolean }) showSliders = false;
  @property({ type: Boolean }) disabled = false;

  static styles = vocalModulatorStyles;

  private _onKey = (e: KeyboardEvent) => {
    if (this.disabled || ['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return;
    const found = VOCAL_PRESETS.find((p) => p.key === e.key);
    if (found) this.selectPreset(found);
    else if (e.key === 'b' || e.key === 'B') this.toggleBypass();
  };

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('keydown', this._onKey);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('keydown', this._onKey);
  }

  selectPreset(p: VocalPresetDef) {
    if (this.disabled) return;
    const same = this.activePreset === p.id;
    this.activePreset = same && this.isEnabled ? null : p.id;
    this.isEnabled = this.activePreset !== null;
    if (this.isEnabled) {
      this.pitchShift = p.pitchShift;
      this.formantShift = p.formantShift;
      this.resonanceHz = p.resonanceHz;
      this.octaveOffset = p.octaveOffset;
    }
    this.dispatchEvent(new CustomEvent('preset-select', { detail: { ...p, isEnabled: this.isEnabled }, bubbles: true, composed: true }));
    this._dispatchModulate();
  }

  toggleBypass() {
    if (this.disabled) return;
    this.isEnabled = !this.isEnabled;
    this._dispatchModulate();
  }

  private _dispatchModulate() {
    this.dispatchEvent(new CustomEvent('vocal-modulate', {
      detail: {
        sessionId: this.sessionId,
        peerId: this.peerId,
        presetName: this.activePreset,
        enabled: this.isEnabled,
        pitchShift: this.pitchShift,
        formantShift: this.formantShift,
        resonanceHz: this.resonanceHz,
        octaveOffset: this.octaveOffset,
      },
      bubbles: true,
      composed: true,
    }));
  }

  private _onSlidersChange(e: CustomEvent<VocalParams>) {
    Object.assign(this, e.detail, { activePreset: 'custom', isEnabled: true });
    this._dispatchModulate();
  }

  render() {
    const cur = VOCAL_PRESETS.find((p) => p.id === this.activePreset);
    return html`
      <div class="modulator-panel">
        <div class="header-row">
          <div class="indicator-group">
            <span class="led-indicator ${this.isEnabled ? 'active' : ''}"></span>
            <span class="title">DM Vocal Modulator</span>
            ${this.isEnabled && cur ? html`<span class="badge-active">${cur.name}</span>` : ''}
          </div>
          <button class="bypass-btn ${this.isEnabled ? 'active' : ''}" @click=${() => this.toggleBypass()} ?disabled=${this.disabled}>
            ${this.isEnabled ? 'MOD ACTIVE' : 'BYPASS'}
          </button>
        </div>
        <div class="preset-grid">
          ${VOCAL_PRESETS.map((p) => html`
            <div class="preset-card ${this.activePreset === p.id && this.isEnabled ? 'selected' : ''}"
                 @click=${() => this.selectPreset(p)} role="button" tabindex="0">
              <span class="preset-icon">${p.icon}</span>
              <span class="preset-name">${p.name}</span>
              <span class="key-badge">${p.key}</span>
            </div>`)}
        </div>
        <button class="toggle-sliders-btn" @click=${() => { this.showSliders = !this.showSliders; }}>
          ${this.showSliders ? 'Hide Advanced DSP' : 'Show Advanced DSP'}
        </button>
        ${this.showSliders ? html`
          <runefoble-vocal-sliders .pitchShift=${this.pitchShift} .formantShift=${this.formantShift}
            .resonanceHz=${this.resonanceHz} .octaveOffset=${this.octaveOffset} ?disabled=${this.disabled}
            @vocal-param-change=${this._onSlidersChange}></runefoble-vocal-sliders>` : ''}
      </div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-vocal-modulator': RunefobleVocalModulator;
  }
}
