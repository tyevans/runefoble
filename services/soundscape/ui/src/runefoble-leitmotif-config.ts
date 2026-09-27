import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { leitmotifConfigStyles } from './runefoble-leitmotif-config.styles.ts';

@customElement('runefoble-leitmotif-config')
export class RunefobleLeitmotifConfig extends LitElement {
  static styles = [leitmotifConfigStyles];

  @property({ type: String }) sessionId = 'default';
  @property({ type: String }) characterId = 'char-nadia';
  @property({ type: String }) characterName = 'Nadia';
  @property({ type: String }) instrumentTimbre = 'lute';
  @property({ type: Number }) tempoMultiplier = 1.0;
  @property({ type: Number }) volumeGain = 100;
  @property({ type: String }) triumphantUrl = '';
  @property({ type: String }) somberUrl = '';
  @property({ type: Boolean }) isDucked = false;

  @state() activePlayingMotif: string | null = null;
  private auditionTimer: number | null = null;

  private readonly onVoiceActivity = (e: Event) => {
    const detail = (e as CustomEvent).detail;
    if (detail?.speaking !== undefined) {
      this.isDucked = Boolean(detail.speaking);
    }
  };

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('runefoble-voice-activity', this.onVoiceActivity);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('runefoble-voice-activity', this.onVoiceActivity);
    if (this.auditionTimer) {
      window.clearTimeout(this.auditionTimer);
      this.auditionTimer = null;
    }
  }

  playAuditionEarcon(motifType: string) {
    try {
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);

      // Distinct waveforms and pitch base per instrument timbre
      const waveMap: Record<string, OscillatorType> = {
        lute: 'triangle',
        brass: 'sawtooth',
        woodwind: 'sine',
        strings: 'sawtooth',
        synth: 'square',
      };
      osc.type = waveMap[this.instrumentTimbre] || 'triangle';

      const baseFreq = motifType === 'triumphant' ? 440 : 220;
      osc.frequency.setValueAtTime(baseFreq * this.tempoMultiplier, ctx.currentTime);

      const duckFactor = this.isDucked ? 0.2512 : 1.0;
      const masterVol = (this.volumeGain / 100) * 0.15 * duckFactor;

      gain.gain.setValueAtTime(0.001, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(masterVol, ctx.currentTime + 0.1);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);

      osc.start();
      osc.stop(ctx.currentTime + 0.5);
    } catch {
      /* graceful acoustic fallback */
    }
  }

  auditionMotif(motifType: 'triumphant' | 'somber') {
    this.activePlayingMotif = motifType;
    this.playAuditionEarcon(motifType);

    this.dispatchEvent(
      new CustomEvent('leitmotif-audition', {
        detail: {
          sessionId: this.sessionId,
          characterId: this.characterId,
          characterName: this.characterName,
          instrumentTimbre: this.instrumentTimbre,
          motifType,
          tempoMultiplier: this.tempoMultiplier,
          volumeGain: this.volumeGain / 100,
          isDucked: this.isDucked,
        },
        bubbles: true,
        composed: true,
      })
    );

    if (this.auditionTimer) window.clearTimeout(this.auditionTimer);
    this.auditionTimer = window.setTimeout(() => {
      this.activePlayingMotif = null;
    }, 2000);
  }

  saveProfile() {
    this.dispatchEvent(
      new CustomEvent('leitmotif-configured', {
        detail: {
          sessionId: this.sessionId,
          characterId: this.characterId,
          characterName: this.characterName,
          instrumentTimbre: this.instrumentTimbre,
          tempoMultiplier: this.tempoMultiplier,
          volumeGain: this.volumeGain / 100,
          triumphantStemUrl: this.triumphantUrl,
          somberStemUrl: this.somberUrl,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  private setTimbre(timbre: string) {
    this.instrumentTimbre = timbre;
    this.dispatchEvent(
      new CustomEvent('leitmotif-timbre-selected', {
        detail: { timbre, characterId: this.characterId },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    const timbres = [
      { id: 'lute', label: '🪕 Lute & Flute' },
      { id: 'brass', label: '🎺 Heroic Brass' },
      { id: 'woodwind', label: '🪵 Woodwind' },
      { id: 'strings', label: '🎻 Solo Cello' },
      { id: 'synth', label: '✨ Arcane Synth' },
    ];

    return html`
      <div class="header">
        <div class="title">
          <span>🎵 Character Leitmotif</span>
        </div>
        <div class="badge-row">
          <span class="badge-timbre">${this.instrumentTimbre}</span>
          ${this.isDucked ? html`<span class="badge-ducked">VOICE DUCKED (-12dB)</span>` : ''}
        </div>
      </div>

      <div class="section">
        <div class="section-label">Character Details</div>
        <div class="char-row">
          <input
            type="text"
            class="input-field"
            .value=${this.characterName}
            placeholder="Character Name"
            @input=${(e: Event) => (this.characterName = (e.target as HTMLInputElement).value)}
          />
          <input
            type="text"
            class="input-field"
            .value=${this.characterId}
            placeholder="Character ID"
            @input=${(e: Event) => (this.characterId = (e.target as HTMLInputElement).value)}
          />
        </div>
      </div>

      <div class="section">
        <div class="section-label">Instrument Timbre Signature</div>
        <div class="timbre-grid">
          ${timbres.map(
            (t) => html`
              <button
                class="timbre-btn ${this.instrumentTimbre === t.id ? 'selected' : ''}"
                @click=${() => this.setTimbre(t.id)}
              >
                ${t.label}
              </button>
            `
          )}
        </div>
      </div>

      <div class="section">
        <div class="section-label">
          <span>Tempo Scaling</span>
          <span class="slider-val">${this.tempoMultiplier.toFixed(2)}x</span>
        </div>
        <div class="slider-control">
          <input
            type="range"
            min="0.5"
            max="2.0"
            step="0.05"
            .value=${String(this.tempoMultiplier)}
            @input=${(e: Event) =>
              (this.tempoMultiplier = Number((e.target as HTMLInputElement).value))}
          />
        </div>

        <div class="section-label">
          <span>Stem Volume Gain</span>
          <span class="slider-val">${this.volumeGain}%</span>
        </div>
        <div class="slider-control">
          <input
            type="range"
            min="0"
            max="150"
            step="5"
            .value=${String(this.volumeGain)}
            @input=${(e: Event) => (this.volumeGain = Number((e.target as HTMLInputElement).value))}
          />
        </div>
      </div>

      <div class="audition-row">
        <button
          class="audition-btn triumphant"
          @click=${() => this.auditionMotif('triumphant')}
        >
          🎺 Triumphant
        </button>
        <button
          class="audition-btn somber"
          @click=${() => this.auditionMotif('somber')}
        >
          🎻 Somber
        </button>
        <button class="audition-btn save" @click=${() => this.saveProfile()}>
          💾 Save
        </button>
      </div>

      ${this.activePlayingMotif
        ? html`
            <div class="playback-indicator">
              <span>▶ Auditioning ${this.activePlayingMotif} motif...</span>
              <span>${this.isDucked ? '(-12dB ducked)' : 'Full Gain'}</span>
            </div>
          `
        : ''}
    `;
  }
}
