import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { soundscapeControlsStyles } from './runefoble-soundscape-controls.styles.ts';

@customElement('runefoble-soundscape-controls')
export class RunefobleSoundscapeControls extends LitElement {
  static styles = [soundscapeControlsStyles];

  @property({ type: String }) sessionId = 'default';
  @property({ type: Number }) tensionScore = 15;
  @property({ type: String }) stemProfile = 'exploration';
  @property({ type: Number }) masterVolume = 85;
  @property({ type: Boolean }) isDucked = false;
  @property({ type: Boolean }) manualOverride = false;
  @property({ type: Array }) activeStems: string[] = ['ambient'];

  @state() private foleyList = [
    { id: 'sword_slash', label: '⚔️ Sword', duck: false },
    { id: 'shield_block', label: '🛡️ Shield', duck: false },
    { id: 'fireball', label: '🔥 Fireball', duck: true },
    { id: 'critical_hit', label: '💥 Crit', duck: true },
    { id: 'thunder_clap', label: '⚡ Thunder', duck: true },
  ];

  private handleVolumeChange(e: Event) {
    const input = e.target as HTMLInputElement;
    this.masterVolume = Number(input.value);
    this.dispatchEvent(
      new CustomEvent('soundscape-volume', {
        detail: { volume: this.masterVolume / 100, sessionId: this.sessionId },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleMoodSelect(mood: string) {
    this.stemProfile = mood;
    this.manualOverride = true;
    this.dispatchEvent(
      new CustomEvent('soundscape-mood', {
        detail: { mood, sessionId: this.sessionId },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleCueTrigger(cueId: string, duckMusic: boolean) {
    this.dispatchEvent(
      new CustomEvent('soundscape-cue', {
        detail: { cueName: cueId, duckMusic, sessionId: this.sessionId },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleDuckToggle() {
    this.isDucked = !this.isDucked;
    this.dispatchEvent(
      new CustomEvent('soundscape-duck', {
        detail: { isDucked: this.isDucked, sessionId: this.sessionId },
        bubbles: true,
        composed: true,
      })
    );
  }

  private getTensionColor(): string {
    if (this.tensionScore < 30) return 'var(--rf-accent-secondary, #2a9d8f)';
    if (this.tensionScore < 60) return 'var(--rf-accent-tertiary, #e9c46a)';
    if (this.tensionScore < 85) return 'var(--rf-accent-primary, #e63946)';
    return '#6a0572';
  }

  render() {
    return html`
      <div class="header">
        <div class="title">Soundscape & Audio</div>
        <div class="badge-row">
          ${this.isDucked
            ? html`<span class="badge-ducked">VOICE DUCKED -12dB</span>`
            : ''}
          <span class="badge-mood ${this.stemProfile}">${this.stemProfile}</span>
        </div>
      </div>

      <div class="section">
        <div class="section-label">
          <span>Encounter Tension</span>
          <span>${this.tensionScore} / 100</span>
        </div>
        <div class="tension-bar">
          <div
            class="tension-fill"
            style="width: ${this.tensionScore}%; background: ${this.getTensionColor()};"
          ></div>
        </div>
      </div>

      <div class="section">
        <div class="section-label">
          <span>Master Volume</span>
          <span class="volume-val">${this.masterVolume}%</span>
        </div>
        <div class="slider-control">
          <input
            type="range"
            min="0"
            max="100"
            .value=${String(this.masterVolume)}
            @input=${this.handleVolumeChange}
          />
        </div>
      </div>

      <div class="section">
        <div class="section-label">
          <span>Audio Stems</span>
        </div>
        <div class="stem-grid">
          <div class="stem-pill ${this.stemProfile === 'exploration' ? 'active' : ''}">
            <span>Ambient Foley</span>
            <span>${this.stemProfile === 'exploration' ? '100%' : '10%'}</span>
          </div>
          <div class="stem-pill ${this.stemProfile === 'tension' ? 'active' : ''}">
            <span>Suspense Strings</span>
            <span>${this.stemProfile === 'tension' ? '90%' : '20%'}</span>
          </div>
          <div class="stem-pill ${this.stemProfile === 'combat' ? 'active' : ''}">
            <span>Combat Drums</span>
            <span>${this.stemProfile === 'combat' ? '100%' : '0%'}</span>
          </div>
          <div class="stem-pill ${this.stemProfile === 'boss' ? 'active' : ''}">
            <span>Boss Climax</span>
            <span>${this.stemProfile === 'boss' ? '100%' : '0%'}</span>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-label">
          <span>DM Mood Override</span>
        </div>
        <div class="mood-buttons">
          <button
            class="mood-btn ${this.stemProfile === 'exploration' ? 'selected' : ''}"
            @click=${() => this.handleMoodSelect('exploration')}
          >
            Exploration
          </button>
          <button
            class="mood-btn ${this.stemProfile === 'tension' ? 'selected' : ''}"
            @click=${() => this.handleMoodSelect('tension')}
          >
            Tension
          </button>
          <button
            class="mood-btn ${this.stemProfile === 'combat' ? 'selected' : ''}"
            @click=${() => this.handleMoodSelect('combat')}
          >
            Combat
          </button>
          <button
            class="mood-btn ${this.stemProfile === 'boss' ? 'selected' : ''}"
            @click=${() => this.handleMoodSelect('boss')}
          >
            Boss
          </button>
        </div>
      </div>

      <div class="section">
        <div class="section-label">
          <span>Tactical Foley FX</span>
          <button class="cue-btn" style="padding: 2px 6px; font-size: 0.65rem;" @click=${this.handleDuckToggle}>
            ${this.isDucked ? 'Unduck' : 'Test Duck'}
          </button>
        </div>
        <div class="foley-buttons">
          ${this.foleyList.map(
            (cue) => html`
              <button
                class="cue-btn"
                @click=${() => this.handleCueTrigger(cue.id, cue.duck)}
              >
                ${cue.label}
              </button>
            `
          )}
        </div>
      </div>
    `;
  }
}
