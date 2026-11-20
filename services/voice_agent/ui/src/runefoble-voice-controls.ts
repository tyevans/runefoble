import { LitElement, html } from 'lit';
import { customElement, property, query, state } from 'lit/decorators.js';
import { renderAudioWaveform } from './waveform-visualizer.ts';
import { voiceControlsStyles } from './runefoble-voice-controls.styles.ts';
import { blobToWavBase64, UtteranceCapture } from './utterance-capture.ts';

/** The detail of `voice-utterance`: one utterance as a base64 16 kHz mono PCM 16-bit WAV. */
export interface VoiceUtteranceDetail {
  audioBase64: string;
}

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/**
 * Push to Talk (TASK-0946). Hold the button, or hold the Space key on it, to record one
 * utterance. On release the element encodes the recording as WAV and emits `voice-utterance`.
 * The element does not know the session and calls no network route. The App Shell posts the
 * audio and sets `sending`, `transcript`, `watcherError` and `uploadError` from the reply.
 * A failure is shown. The element never shows a transcript that it did not receive.
 */
@customElement('runefoble-voice-controls')
export class RunefobleVoiceControls extends LitElement {
  @property({ type: Boolean }) disabled = false;
  @property({ type: String }) channelName = 'Collaborative Voice Channel';
  @property({ type: Array }) activeFilters: string[] = [];
  /** True while the button is held and the microphone records. */
  @property({ type: Boolean, reflect: true }) holding = false;
  /** Set by the App Shell while the upload is out. */
  @property({ type: Boolean }) sending = false;
  /** The transcript that the transcribe route returned for the last utterance. */
  @property({ type: String }) transcript = '';
  /** Why The Watcher did not take the last transcript (`watcher_error` of the reply). */
  @property({ type: String }) watcherError = '';
  /** Why the last upload failed. */
  @property({ type: String }) uploadError = '';

  @state() private preparing = false;
  @state() private captureError = '';
  @state() private audioLevel = 0;
  @query('.waveform-canvas') private canvasElement?: HTMLCanvasElement;

  private opening: Promise<UtteranceCapture> | null = null;
  private analyser: AnalyserNode | null = null;
  private animFrameId: number | null = null;

  static styles = voiceControlsStyles;

  firstUpdated() {
    this.drawLevel();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    const opening = this.opening;
    this.opening = null;
    this.holding = false;
    this.stopMeter();
    opening?.then((capture) => capture.cancel(), () => undefined);
  }

  private get busy(): boolean {
    return this.preparing || this.sending;
  }

  private async beginHold(): Promise<void> {
    if (this.disabled || this.holding || this.busy) return;
    this.captureError = '';
    this.holding = true;
    const opening = UtteranceCapture.open();
    this.opening = opening;
    try {
      const capture = await opening;
      if (this.holding && this.opening === opening) this.startMeter(capture.analyser);
    } catch (err) {
      if (this.opening === opening) {
        this.opening = null;
        this.holding = false;
      }
      this.captureError = `The microphone is not available: ${errorText(err)}`;
    }
  }

  private async endHold(): Promise<void> {
    if (!this.holding) return;
    this.holding = false;
    const opening = this.opening;
    this.opening = null;
    this.stopMeter();
    if (!opening) return;
    let capture: UtteranceCapture;
    try {
      capture = await opening;
    } catch {
      return; // beginHold shows the microphone failure.
    }
    this.preparing = true;
    try {
      const audioBase64 = await blobToWavBase64(await capture.stop());
      this.dispatchEvent(
        new CustomEvent<VoiceUtteranceDetail>('voice-utterance', {
          detail: { audioBase64 },
          bubbles: true,
          composed: true,
        })
      );
    } catch (err) {
      this.captureError = `The utterance was not sent: ${errorText(err)}`;
    } finally {
      this.preparing = false;
    }
  }

  private onKeyDown(e: KeyboardEvent): void {
    if (e.code !== 'Space') return;
    e.preventDefault();
    if (!e.repeat) void this.beginHold();
  }

  private onKeyUp(e: KeyboardEvent): void {
    if (e.code !== 'Space') return;
    e.preventDefault();
    void this.endHold();
  }

  private startMeter(analyser: AnalyserNode): void {
    this.analyser = analyser;
    const loop = () => {
      if (this.analyser === null) return;
      this.drawLevel();
      this.animFrameId = requestAnimationFrame(loop);
    };
    this.animFrameId = requestAnimationFrame(loop);
  }

  private stopMeter(): void {
    if (this.animFrameId !== null) cancelAnimationFrame(this.animFrameId);
    this.animFrameId = null;
    this.analyser = null;
    this.drawLevel();
  }

  private drawLevel(): void {
    const canvas = this.canvasElement;
    if (!canvas) return;
    const metrics = renderAudioWaveform({ canvas, analyser: this.analyser, activeFilters: this.activeFilters });
    this.audioLevel = metrics.level;
    if (this.analyser) {
      this.dispatchEvent(
        new CustomEvent('voice-level', {
          detail: { level: metrics.level, peak: metrics.peak },
          bubbles: true,
          composed: true,
        })
      );
    }
  }

  private buttonLabel(): string {
    if (this.holding) return 'Release to Send';
    if (this.busy) return 'Sending...';
    return 'Push to Talk';
  }

  private renderOutcome() {
    const error = this.captureError || this.uploadError;
    if (error) return html`<div class="utterance-error" role="alert">${error}</div>`;
    if (this.busy) return html`<div class="utterance-status" role="status">Sending the utterance...</div>`;
    if (!this.transcript) return '';
    return html`<div class="utterance-result" role="status">
        <span class="utterance-label">Heard:</span> <q class="utterance-transcript">${this.transcript}</q>
      </div>
      ${this.watcherError
        ? html`<div class="utterance-error watcher-error" role="alert">The Watcher did not act: ${this.watcherError}</div>`
        : ''}`;
  }

  render() {
    return html`
      <div class="voice-control-panel">
        <div class="header-row">
          <div class="channel-header">
            <span class="status-indicator ${this.holding ? 'live' : ''}"></span>
            <strong class="channel-title">${this.channelName}</strong>
          </div>
          <div class="status-badges">
            ${this.activeFilters.map((filter) => html`<span class="badge badge-dsp">DSP: ${filter}</span>`)}
          </div>
        </div>

        <div class="main-controls-row">
          <div class="visualizer-wrapper">
            <div class="canvas-container">
              <canvas class="waveform-canvas" width="320" height="44" aria-label="Microphone input level"></canvas>
            </div>
            <div class="metrics-panel">
              <span>LEVEL: ${Math.round(this.audioLevel * 100)}%</span>
            </div>
          </div>

          <button
            class="mic-button ${this.holding ? 'listening' : ''}"
            ?disabled=${this.disabled || this.busy}
            aria-pressed=${this.holding ? 'true' : 'false'}
            aria-label="Hold to talk"
            @pointerdown=${(e: PointerEvent) => { if (e.button === 0) void this.beginHold(); }}
            @pointerup=${() => void this.endHold()}
            @pointerleave=${() => void this.endHold()}
            @pointercancel=${() => void this.endHold()}
            @keydown=${this.onKeyDown}
            @keyup=${this.onKeyUp}
            @contextmenu=${(e: Event) => e.preventDefault()}
          >
            🎙️ ${this.buttonLabel()}
          </button>
        </div>

        ${this.renderOutcome()}

        <div class="panel-instruction">
          Hold the button (or Space) and speak: "Move my warrior to the chest", "Cast cure wounds on Valeros".
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-voice-controls': RunefobleVoiceControls;
  }
}
