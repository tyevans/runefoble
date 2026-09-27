import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { settingsStyles } from './styles/settings.styles.ts';

@customElement('duplex-settings-panel')
export class DuplexSettingsPanel extends LitElement {
  @property({ type: Number }) vadSensitivity = 75;
  @property({ type: Number }) duckingGainDb = -12;
  @property({ type: Boolean }) aecEnabled = true;
  @property({ type: Number }) aecSuppressionDb = 35;

  static styles = settingsStyles;

  private _onVadInput(e: Event) {
    const val = Number((e.target as HTMLInputElement).value);
    this.vadSensitivity = val;
    this.dispatchEvent(new CustomEvent('vad-sensitivity-change', {
      detail: { sensitivity: val },
      bubbles: true,
      composed: true,
    }));
  }

  private _onDuckingInput(e: Event) {
    const val = Number((e.target as HTMLInputElement).value);
    this.duckingGainDb = val;
    this.dispatchEvent(new CustomEvent('ducking-gain-change', {
      detail: { gainDb: val },
      bubbles: true,
      composed: true,
    }));
  }

  private _onAecToggle(e: Event) {
    const enabled = (e.target as HTMLInputElement).checked;
    this.aecEnabled = enabled;
    this.dispatchEvent(new CustomEvent('aec-toggle', {
      detail: { enabled, suppressionDb: this.aecSuppressionDb },
      bubbles: true,
      composed: true,
    }));
  }

  private _onAecGainInput(e: Event) {
    const val = Number((e.target as HTMLInputElement).value);
    this.aecSuppressionDb = val;
    this.dispatchEvent(new CustomEvent('aec-toggle', {
      detail: { enabled: this.aecEnabled, suppressionDb: val },
      bubbles: true,
      composed: true,
    }));
  }

  render() {
    return html`
      <div class="settings-card" role="region" aria-label="Duplex Audio Settings">
        <div class="panel-header">
          <span>⚙️ Duplex & VAD Calibration</span>
          <span class="val-badge">${this.aecEnabled ? 'AEC ON' : 'AEC OFF'}</span>
        </div>
        <div class="control-row">
          <label class="control-label" for="vad-slider">
            <span>Interruption Sensitivity (VAD Threshold)</span>
            <span class="val-badge">${this.vadSensitivity}%</span>
          </label>
          <input
            id="vad-slider"
            type="range"
            min="10"
            max="100"
            step="1"
            .value=${String(this.vadSensitivity)}
            @input=${this._onVadInput}
            aria-label="Interruption Sensitivity"
          />
        </div>
        <div class="control-row">
          <label class="control-label" for="ducking-slider">
            <span>Acoustic Ducking Gain</span>
            <span class="val-badge">${this.duckingGainDb} dB</span>
          </label>
          <input
            id="ducking-slider"
            type="range"
            min="-30"
            max="0"
            step="1"
            .value=${String(this.duckingGainDb)}
            @input=${this._onDuckingInput}
            aria-label="Acoustic Ducking Gain"
          />
        </div>
        <div class="control-row">
          <label class="checkbox-row">
            <input
              type="checkbox"
              .checked=${this.aecEnabled}
              @change=${this._onAecToggle}
              aria-label="Enable Acoustic Echo Cancellation"
            />
            <span>Acoustic Echo Cancellation (AEC)</span>
          </label>
          ${this.aecEnabled
            ? html`
                <div class="control-row" style="margin-top: 4px;">
                  <label class="control-label" for="aec-slider">
                    <span>AEC Target Suppression</span>
                    <span class="val-badge">&gt;${this.aecSuppressionDb} dB ERLE</span>
                  </label>
                  <input
                    id="aec-slider"
                    type="range"
                    min="15"
                    max="50"
                    step="1"
                    .value=${String(this.aecSuppressionDb)}
                    @input=${this._onAecGainInput}
                    aria-label="AEC Target Suppression"
                  />
                </div>
              `
            : ''}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'duplex-settings-panel': DuplexSettingsPanel;
  }
}
