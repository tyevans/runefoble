import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('runefoble-handout-viewer')
export class RunefobleHandoutViewer extends LitElement {
  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      padding: 16px;
      color: var(--rf-text-primary, #121212);
      width: 520px;
      max-width: 100%;
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      box-sizing: border-box;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 8px;
      border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      margin-bottom: 12px;
    }
    .title { font-size: 1.1rem; font-weight: 800; letter-spacing: -0.02em; }
    .badges { display: flex; gap: 6px; }
    .badge { font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border: 1px solid var(--rf-border-color, #121212); background: var(--rf-accent-tertiary, #ffb703); }
    .badge.broken { background: #a8dadc; }
    .badge.uv { background: #c77dff; color: #ffffff; }
    .controls { display: flex; gap: 8px; margin-bottom: 12px; }
    .btn {
      padding: 6px 12px;
      font-size: 0.8rem;
      font-weight: 700;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      cursor: pointer;
      box-shadow: 2px 2px 0px #121212;
      background: var(--rf-accent-primary, #e63946);
      color: #ffffff;
    }
    .btn.secondary {
      background: var(--rf-bg-surface, #ffffff);
      color: var(--rf-text-primary, #121212);
    }
    .btn:hover {
      transform: translate(-1px, -1px);
      box-shadow: 3px 3px 0px #121212;
    }
    .parchment {
      position: relative;
      background: #f4ecd8;
      border: 3px double #8c6b45;
      padding: 24px;
      min-height: 220px;
      border-radius: 2px;
      box-shadow: inset 0 0 30px rgba(139, 69, 19, 0.25);
      overflow: hidden;
      cursor: default;
    }
    .parchment.uv-active {
      background: #1a162b;
      box-shadow: inset 0 0 40px rgba(138, 43, 226, 0.4);
      color: #e0d0cc;
    }
    .calligraphy {
      font-family: Georgia, 'Times New Roman', serif;
      line-height: 1.8;
      font-size: 0.95rem;
      color: #2b1d0c;
      white-space: pre-line;
      transition: filter 0.3s ease;
    }
    .calligraphy.sealed {
      filter: blur(4px);
      user-select: none;
    }
    .calligraphy.uv-active {
      color: #9d8189;
    }
    .seal-container {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
      z-index: 10;
    }
    .wax-seal {
      width: 76px;
      height: 76px;
      border-radius: 50%;
      background: radial-gradient(circle at 35% 35%, #b22222, #8b0000 65%, #4a0000);
      border: 3px solid #3b0000;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5), inset 0 2px 4px rgba(255, 255, 255, 0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      color: #ffcccc;
      font-weight: 800;
      transition: transform 0.15s ease;
    }
    .wax-seal:hover {
      transform: scale(1.06);
    }
    .wax-seal.cracking {
      animation: shake 0.3s ease;
    }
    @keyframes shake {
      0%, 100% { transform: scale(1.05) rotate(0deg); }
      25% { transform: scale(1.05) rotate(-5deg); }
      75% { transform: scale(1.05) rotate(5deg); }
    }
    .seal-label {
      font-size: 0.75rem;
      font-weight: 800;
      margin-top: 6px;
      color: #8b0000;
      background: rgba(255, 255, 255, 0.85);
      padding: 2px 6px;
      border: 1px solid #8b0000;
    }
    .uv-layer {
      position: absolute;
      inset: 0;
      pointer-events: none;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      box-sizing: border-box;
    }
    .uv-text {
      color: #00ffcc;
      text-shadow: 0 0 10px #00ffcc, 0 0 20px #00ffcc;
      font-family: monospace;
      font-weight: 700;
      font-size: 1.1rem;
      letter-spacing: 0.1em;
      text-align: center;
      background: rgba(0, 0, 0, 0.4);
      padding: 12px;
      border: 1px dashed #00ffcc;
    }
  `;

  @property({ type: String }) title = 'Intercepted Courier Dispatch';
  @property({ type: String }) handoutType = 'letter';
  @property({ type: String }) paperTexture = 'weathered_parchment';
  @property({ type: String }) calligraphyFont = 'royal_chancery';
  @property({ type: String }) content = 'By royal decree of Neverwinter, the Sunken Spire is declared forbidden ground.';
  @property({ type: Boolean }) hasWaxSeal = true;
  @property({ type: String }) sealState: 'intact' | 'broken' = 'intact';
  @property({ type: String }) sealColor = 'crimson';
  @property({ type: String }) sealStamp = 'raven_crest';
  @property({ type: Boolean }) hasInvisibleInk = false;
  @property({ type: String }) secretInkText = '';
  @property({ type: Boolean }) uvMode = false;

  @state() private isCracking = false;

  breakSeal() {
    if (this.sealState === 'broken') return;
    this.isCracking = true;
    this.synthesizeCrackAudio();

    setTimeout(() => {
      this.sealState = 'broken';
      this.isCracking = false;
      this.dispatchEvent(
        new CustomEvent('seal-broken', {
          detail: {
            title: this.title,
            breakForce: 12.5,
            audioEffect: 'wax_crack_crisp_01.wav',
          },
          bubbles: true,
          composed: true,
        })
      );
    }, 280);
  }

  toggleUvMode() {
    this.uvMode = !this.uvMode;
    this.dispatchEvent(
      new CustomEvent('uv-toggled', {
        detail: { uvMode: this.uvMode, secretRevealed: this.uvMode && this.hasInvisibleInk },
        bubbles: true,
        composed: true,
      })
    );
  }

  private synthesizeCrackAudio() {
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(440, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(80, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.16);
    } catch {
      // AudioContext optional in headless/test environments
    }
  }

  render() {
    const isSealed = this.hasWaxSeal && this.sealState === 'intact';

    return html`
      <div class="header">
        <span class="title">${this.title}</span>
        <div class="badges">
          <span class="badge">${this.handoutType}</span>
          ${this.hasWaxSeal
            ? html`<span class="badge ${this.sealState === 'broken' ? 'broken' : ''}">
                ${this.sealState === 'intact' ? 'Wax Sealed' : 'Seal Broken'}
              </span>`
            : ''}
          ${this.hasInvisibleInk
            ? html`<span class="badge uv">${this.uvMode ? 'UV Active' : 'Secret Ink'}</span>`
            : ''}
        </div>
      </div>

      <div class="controls">
        ${isSealed
          ? html`<button class="btn" @click=${this.breakSeal}>Crack Wax Seal</button>`
          : ''}
        ${this.hasInvisibleInk
          ? html`<button class="btn secondary" @click=${this.toggleUvMode}>
              ${this.uvMode ? 'Normal Light' : 'Simulate UV Torch'}
            </button>`
          : ''}
      </div>

      <div class="parchment ${this.uvMode ? 'uv-active' : ''}">
        <div class="calligraphy ${isSealed ? 'sealed' : ''} ${this.uvMode ? 'uv-active' : ''}">
          ${this.content}
        </div>

        ${isSealed
          ? html`
              <div class="seal-container">
                <div
                  class="wax-seal ${this.isCracking ? 'cracking' : ''}"
                  @click=${this.breakSeal}
                  title="Click to break wax seal"
                >
                  <svg width="40" height="40" viewBox="0 0 100 100" fill="currentColor">
                    <path d="M 50 20 C 40 25 35 35 38 48 C 30 50 25 60 28 72 C 35 68 42 67 48 70 C 45 78 52 82 58 79 C 62 68 65 52 62 38 C 60 28 55 22 50 20 Z" />
                  </svg>
                </div>
                <div class="seal-label">Break Seal to Open</div>
              </div>
            `
          : ''}

        ${this.uvMode && this.hasInvisibleInk && this.secretInkText
          ? html`
              <div class="uv-layer">
                <div class="uv-text">
                  ᚱᚢᚾᛖ: ${this.secretInkText}
                </div>
              </div>
            `
          : ''}
      </div>
    `;
  }
}
