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
  @property({ type: Object }) stemVolumes: Record<string, number> = {
    melody: 80, percussion: 70, drone: 60, ambient: 90,
  };

  @state() private foleyList = [
    { id: 'thunder', label: '⚡ Thunder', duck: true },
    { id: 'door_slam', label: '🚪 Door Slam', duck: false },
    { id: 'steel_clash', label: '⚔️ Steel Clash', duck: false },
    { id: 'roar', label: '🦁 Roar', duck: true },
    { id: 'fireball', label: '🔥 Fireball', duck: true },
    { id: 'shield_block', label: '🛡️ Shield', duck: false },
  ];
  @state() private customName = '';
  @state() private customLabel = '';
  private duckTimer: number | null = null;
  private readonly onVoiceActivity = (e: Event) => {
    const detail = (e as CustomEvent).detail;
    if (detail?.speaking !== undefined) {
      if (detail.speaking) this.triggerDucking(detail.durationMs || 2500, 'voice');
      else this.clearDucking();
    }
  };

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('runefoble-voice-activity', this.onVoiceActivity);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('runefoble-voice-activity', this.onVoiceActivity);
    this.clearDucking();
  }

  playEarcon(cueId: string) {
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      const freq = cueId === 'thunder' ? 70 : cueId === 'roar' ? 110 : cueId === 'steel_clash' ? 750 : 440;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
      osc.start();
      osc.stop(ctx.currentTime + 0.25);
    } catch { /* graceful fallback */ }
  }

  triggerDucking(durationMs = 2000, reason = 'cue') {
    this.isDucked = true;
    this.dispatchCustom('soundscape-duck', { isDucked: true, reason, sessionId: this.sessionId });
    if (this.duckTimer) window.clearTimeout(this.duckTimer);
    if (durationMs > 0) {
      this.duckTimer = window.setTimeout(() => this.clearDucking(), durationMs);
    }
  }

  private clearDucking() {
    if (this.duckTimer) { window.clearTimeout(this.duckTimer); this.duckTimer = null; }
    if (this.isDucked) {
      this.isDucked = false;
      this.dispatchCustom('soundscape-duck', { isDucked: false, sessionId: this.sessionId });
    }
  }

  private dispatchCustom(name: string, detail: unknown) {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }

  private handleVolumeChange(e: Event) {
    this.masterVolume = Number((e.target as HTMLInputElement).value);
    this.dispatchCustom('soundscape-volume', { volume: this.masterVolume / 100, sessionId: this.sessionId });
  }

  private handleStemChange(stem: string, e: Event) {
    const val = Number((e.target as HTMLInputElement).value);
    this.stemVolumes = { ...this.stemVolumes, [stem]: val };
    this.dispatchCustom('soundscape-stem-volume', { stem, volume: val / 100, stemVolumes: this.stemVolumes, sessionId: this.sessionId });
  }

  private handleMoodSelect(mood: string) {
    this.stemProfile = mood;
    this.manualOverride = true;
    this.dispatchCustom('soundscape-mood', { mood, sessionId: this.sessionId });
  }

  private handleCueTrigger(cueId: string, duckMusic: boolean) {
    this.playEarcon(cueId);
    this.dispatchCustom('soundscape-cue', { cueName: cueId, duckMusic, sessionId: this.sessionId });
    if (duckMusic) this.triggerDucking(2000, cueId);
  }

  private handleDuckToggle() {
    if (this.isDucked) this.clearDucking();
    else this.triggerDucking(0, 'manual');
  }

  private handleAddCue() {
    if (!this.customName || !this.customLabel) return;
    this.foleyList = [...this.foleyList, { id: this.customName, label: this.customLabel, duck: false }];
    this.customName = '';
    this.customLabel = '';
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
          ${this.isDucked ? html`<span class="badge-ducked">VOICE DUCKED -12dB</span>` : ''}
          <span class="badge-mood ${this.stemProfile}">${this.stemProfile}</span>
        </div>
      </div>
      <div class="section">
        <div class="section-label">
          <span>Encounter Tension (${this.tensionScore}/100)</span>
          <button class="toggle-btn ${this.manualOverride ? 'active' : ''}" @click=${() => { this.manualOverride = !this.manualOverride; }}>
            ${this.manualOverride ? 'Override: ON' : 'Override: AUTO'}
          </button>
        </div>
        <div class="tension-bar">
          <div class="tension-fill" style="width: ${this.tensionScore}%; background: ${this.getTensionColor()};"></div>
        </div>
      </div>
      <div class="section">
        <div class="section-label">
          <span>Master Volume</span><span class="volume-val">${this.masterVolume}%</span>
        </div>
        <div class="slider-control">
          <input type="range" min="0" max="100" .value=${String(this.masterVolume)} @input=${this.handleVolumeChange} />
        </div>
      </div>
      <div class="section">
        <div class="section-label"><span>Multi-Channel Stem Sliders</span></div>
        <div class="stem-sliders-grid">
          ${['melody', 'percussion', 'drone', 'ambient'].map((stem) => html`
            <div class="stem-slider-row">
              <div class="stem-label-row"><span>${stem}</span><span>${this.stemVolumes[stem] ?? 70}%</span></div>
              <input type="range" min="0" max="100" .value=${String(this.stemVolumes[stem] ?? 70)} @input=${(e: Event) => this.handleStemChange(stem, e)} />
            </div>
          `)}
        </div>
      </div>
      <div class="section">
        <div class="section-label"><span>DM Mood Override</span></div>
        <div class="mood-buttons">
          ${['exploration', 'tension', 'combat', 'boss'].map((m) => html`
            <button class="mood-btn ${this.stemProfile === m ? 'selected' : ''}" @click=${() => this.handleMoodSelect(m)}>${m}</button>
          `)}
        </div>
      </div>
      <div class="section">
        <div class="section-label">
          <span>Tactile Soundboard Grid</span>
          <button class="toggle-btn" @click=${this.handleDuckToggle}>${this.isDucked ? 'Unduck' : 'Test Duck'}</button>
        </div>
        <div class="foley-grid">
          ${this.foleyList.map((cue) => html`
            <button class="cue-btn" @click=${() => this.handleCueTrigger(cue.id, cue.duck)}>${cue.label}</button>
          `)}
        </div>
        <div class="add-cue-row">
          <input class="mini-input" placeholder="id (e.g. clang)" .value=${this.customName} @input=${(e: Event) => { this.customName = (e.target as HTMLInputElement).value; }} />
          <input class="mini-input" placeholder="label (e.g. 🔔 Bell)" .value=${this.customLabel} @input=${(e: Event) => { this.customLabel = (e.target as HTMLInputElement).value; }} />
          <button class="toggle-btn" @click=${this.handleAddCue}>+ Add</button>
        </div>
      </div>
    `;
  }
}
