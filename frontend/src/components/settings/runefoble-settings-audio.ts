import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { settingsModalStyles } from '../runefoble-settings-modal.styles.ts';

@customElement('runefoble-settings-audio')
export class RunefobleSettingsAudio extends LitElement {
  static styles = settingsModalStyles;

  @property({ type: String }) audioInputDevice: string = 'default';
  @property({ type: Boolean }) noiseSuppression: boolean = true;
  @property({ type: String }) permissionStatus: string = 'granted';

  private handleDeviceChange(e: Event): void {
    const value = (e.target as HTMLSelectElement).value;
    this.audioInputDevice = value;
    this.dispatchEvent(
      new CustomEvent('device-change', {
        detail: { device: value },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleNoiseChange(e: Event): void {
    const checked = (e.target as HTMLInputElement).checked;
    this.noiseSuppression = checked;
    this.dispatchEvent(
      new CustomEvent('noise-suppression-change', {
        detail: { noiseSuppression: checked },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    return html`
      <div class="form-group">
        <label class="form-label" for="audio-input-device">Microphone Input Device</label>
        <select
          id="audio-input-device"
          class="form-select"
          .value=${this.audioInputDevice}
          @change=${this.handleDeviceChange}
        >
          <option value="default">Default System Microphone</option>
          <option value="studio-mic">Studio Condenser Mic (USB Audio)</option>
          <option value="headset">Gaming Headset Microphone</option>
        </select>
      </div>

      <div class="form-group">
        <label class="checkbox-row">
          <input
            type="checkbox"
            .checked=${this.noiseSuppression}
            @change=${this.handleNoiseChange}
          />
          Adaptive Noise Suppression & Echo Cancellation
        </label>
      </div>

      <div class="form-group">
        <div class="mic-status" style="display: flex; align-items: center; gap: 8px; font-size: 0.8rem; color: var(--rf-text-muted);">
          <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #22c55e;"></span>
          <span>Microphone Permission: Ready</span>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-settings-audio': RunefobleSettingsAudio;
  }
}
