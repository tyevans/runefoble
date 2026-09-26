import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('runefoble-voice-controls')
export class RunefobleVoiceControls extends LitElement {
  @property({ type: Boolean }) isListening = false;
  @property({ type: Boolean }) disabled = false;
  @property({ type: String }) channelName = 'Collaborative Voice Channel';

  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      color: var(--rf-text-primary, #121212);
    }
    .voice-control-panel {
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      box-sizing: border-box;
      transition: background-color 0.2s ease, border-color 0.2s ease;
    }
    .channel-header {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .status-indicator {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background-color: var(--rf-text-muted, #4b5563);
      display: inline-block;
      transition: background-color 0.2s ease;
    }
    .status-indicator.live {
      background-color: var(--rf-accent-primary, #e63946);
      box-shadow: 0 0 6px var(--rf-accent-primary, #e63946);
    }
    .channel-title {
      font-weight: 700;
      font-size: 1rem;
      color: var(--rf-text-primary, #121212);
    }
    .panel-instruction {
      font-size: 0.85rem;
      color: var(--rf-text-muted, #4b5563);
      margin-top: 4px;
    }
    .mic-button {
      background: var(--rf-accent-primary, #e63946);
      color: var(--rf-color-light, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      padding: 10px 20px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: inherit;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .mic-button:hover:not(:disabled) {
      transform: translate(-1px, -1px);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    }
    .mic-button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .mic-button.listening {
      background: var(--rf-accent-tertiary, #ffb703);
      color: #121212;
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
      0% {
        box-shadow: 0 0 0 0 rgba(230, 57, 70, 0.7);
      }
      70% {
        box-shadow: 0 0 0 10px rgba(230, 57, 70, 0);
      }
      100% {
        box-shadow: 0 0 0 0 rgba(230, 57, 70, 0);
      }
    }
  `;

  private _handleToggle() {
    if (this.disabled) return;
    this.dispatchEvent(
      new CustomEvent('voice-toggle', {
        detail: { isListening: !this.isListening },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    return html`
      <div class="voice-control-panel">
        <div>
          <div class="channel-header">
            <span class="status-indicator ${this.isListening ? 'live' : ''}"></span>
            <strong class="channel-title">${this.channelName}</strong>
          </div>
          <div class="panel-instruction">
            Speak naturally: "Move my warrior to the chest", "Cast cure wounds on Valeros", "What does the altar look like?"
          </div>
        </div>
        <button
          class="mic-button ${this.isListening ? 'listening' : ''}"
          ?disabled=${this.disabled}
          @click=${this._handleToggle}
          aria-label="${this.isListening ? 'Mute microphone' : 'Start speaking'}"
        >
          🎙️ ${this.isListening ? 'Streaming Audio (Click to Mute)' : 'Push to Talk'}
        </button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-voice-controls': RunefobleVoiceControls;
  }
}
