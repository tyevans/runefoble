import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

export interface VocalParams {
  pitchShift: number;
  formantShift: number;
  resonanceHz: number;
  octaveOffset: number;
}

@customElement('runefoble-vocal-sliders')
export class RunefobleVocalSliders extends LitElement {
  @property({ type: Number }) pitchShift = 0.0;
  @property({ type: Number }) formantShift = 1.0;
  @property({ type: Number }) resonanceHz = 0.0;
  @property({ type: Number }) octaveOffset = 0.0;
  @property({ type: Boolean }) disabled = false;

  static styles = css`
    :host { display: block; }
    .sliders-panel {
      background: var(--rf-bg-inset, #f4f4f5);
      border: 1px solid var(--rf-border-color, #18181b);
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .slider-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 0.75rem; }
    .slider-label { font-weight: 700; min-width: 100px; text-transform: uppercase; }
    .slider-input { flex: 1; cursor: pointer; accent-color: var(--rf-accent-primary, #e11d48); }
    .slider-val { font-family: monospace; font-weight: 700; min-width: 52px; text-align: right; }
    .footer-row { display: flex; justify-content: flex-end; margin-top: 4px; }
    .reset-btn {
      background: var(--rf-bg-surface, #ffffff);
      border: 1px solid var(--rf-border-color, #18181b);
      font-size: 0.7rem;
      font-weight: 700;
      padding: 2px 8px;
      cursor: pointer;
    }
  `;

  private _onInput(key: keyof VocalParams, val: number) {
    if (this.disabled) return;
    (this as unknown as Record<string, unknown>)[key] = val;
    this.dispatchEvent(
      new CustomEvent<VocalParams>('vocal-param-change', {
        detail: {
          pitchShift: this.pitchShift,
          formantShift: this.formantShift,
          resonanceHz: this.resonanceHz,
          octaveOffset: this.octaveOffset,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  resetDefaults() {
    this.pitchShift = 0.0;
    this.formantShift = 1.0;
    this.resonanceHz = 0.0;
    this.octaveOffset = 0.0;
    this._onInput('pitchShift', 0.0);
  }

  render() {
    const sliders: Array<{ key: keyof VocalParams; label: string; min: number; max: number; step: number; val: string }> = [
      { key: 'pitchShift', label: 'Pitch Shift', min: -12, max: 12, step: 0.5, val: `${this.pitchShift > 0 ? '+' : ''}${this.pitchShift.toFixed(1)} st` },
      { key: 'formantShift', label: 'Formant Shift', min: 0.5, max: 2.0, step: 0.05, val: `${this.formantShift.toFixed(2)}x` },
      { key: 'resonanceHz', label: 'Resonance', min: 0, max: 4000, step: 20, val: `${Math.round(this.resonanceHz)} Hz` },
      { key: 'octaveOffset', label: 'Octave Offset', min: -1.0, max: 1.0, step: 0.1, val: `${this.octaveOffset > 0 ? '+' : ''}${this.octaveOffset.toFixed(1)} oct` },
    ];
    return html`
      <div class="sliders-panel">
        ${sliders.map((s) => html`
          <div class="slider-row">
            <span class="slider-label">${s.label}</span>
            <input type="range" class="slider-input" aria-label="${s.label}" min="${s.min}" max="${s.max}" step="${s.step}"
              .value=${String((this as unknown as Record<string, unknown>)[s.key])} ?disabled=${this.disabled}
              @input=${(e: Event) => this._onInput(s.key, parseFloat((e.target as HTMLInputElement).value))} />
            <span class="slider-val">${s.val}</span>
          </div>
        `)}
        <div class="footer-row">
          <button class="reset-btn" @click=${() => this.resetDefaults()} ?disabled=${this.disabled}>Reset DSP</button>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-vocal-sliders': RunefobleVocalSliders;
  }
}
