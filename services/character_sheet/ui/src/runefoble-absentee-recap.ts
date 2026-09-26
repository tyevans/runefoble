import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { absenteeRecapStyles } from './runefoble-absentee-recap.styles.ts';

@customElement('runefoble-absentee-recap')
export class RunefobleAbsenteeRecap extends LitElement {
  @property({ type: String }) characterName = '';
  @property({ type: String }) persona = '';
  @property({ type: Array }) penalties: string[] = [];
  @property({ type: String }) narrative = '';
  @property({ type: Array }) highlights: string[] = [];
  @property({ type: Number }) hpDelta = 0;
  @property({ type: Array }) itemsAcquired: string[] = [];
  @property({ type: Boolean }) isPlayingAudio = false;

  static styles = [absenteeRecapStyles];

  private toggleAudio() {
    this.isPlayingAudio = !this.isPlayingAudio;
    this.dispatchEvent(
      new CustomEvent('audio-toggle', {
        detail: { isPlaying: this.isPlayingAudio, character: this.characterName },
        bubbles: true,
        composed: true,
      })
    );
  }

  private renderPenaltyBadge(penalty: string) {
    const p = penalty.toLowerCase().trim();
    let cssClass = 'penalty-default';
    let icon = '⚠️';

    if (p === 'drunk') {
      cssClass = 'penalty-drunk';
      icon = '🍺';
    } else if (p === 'foolishness') {
      cssClass = 'penalty-foolishness';
      icon = '🃏';
    } else if (p === 'greed') {
      cssClass = 'penalty-greed';
      icon = '🪙';
    } else if (p === 'cowardice') {
      cssClass = 'penalty-cowardice';
      icon = '🛡️';
    }

    return html`
      <span class="penalty-badge ${cssClass}">
        <span>${icon}</span>
        <span>${penalty}</span>
      </span>
    `;
  }

  render() {
    const hpClass =
      this.hpDelta > 0 ? 'hp-positive' : this.hpDelta < 0 ? 'hp-negative' : 'hp-neutral';
    const hpText =
      this.hpDelta > 0 ? `+${this.hpDelta} HP` : this.hpDelta < 0 ? `${this.hpDelta} HP` : 'No HP Change';

    return html`
      <div class="modal-glow"></div>

      <div class="header">
        <div class="title-area">
          <h2>📜 Absentee Session Chronicle</h2>
          <div class="hero-meta">
            Stand-in recap for <strong>${this.characterName || 'Unknown Adventurer'}</strong>
          </div>
        </div>
        ${this.persona ? html`<span class="persona-tag">Persona: ${this.persona}</span>` : ''}
      </div>

      ${this.penalties && this.penalties.length > 0
        ? html`
            <div class="penalties-row">
              ${this.penalties.map((p) => this.renderPenaltyBadge(p))}
            </div>
          `
        : ''}

      <div class="status-strip">
        <div class="status-item">
          <span>❤️ Health Delta:</span>
          <span class="${hpClass}">${hpText}</span>
        </div>
        ${this.itemsAcquired && this.itemsAcquired.length > 0
          ? html`
              <div class="status-item">
                <span>🎒 Loot:</span>
                <span style="color: #fbbf24;">${this.itemsAcquired.join(', ')}</span>
              </div>
            `
          : ''}
      </div>

      ${this.narrative
        ? html`
            <div class="narrative-box">
              "${this.narrative}"
            </div>
          `
        : ''}

      ${this.highlights && this.highlights.length > 0
        ? html`
            <div class="section-title">Session Exploits & Highlights</div>
            <ul class="highlights-list">
              ${this.highlights.map(
                (h) => html`
                  <li class="highlight-item">
                    <span class="highlight-icon">⚡</span>
                    <span>${h}</span>
                  </li>
                `
              )}
            </ul>
          `
        : ''}

      <div class="audio-player-bar">
        <button
          class="play-btn ${this.isPlayingAudio ? 'playing' : ''}"
          @click=${this.toggleAudio}
          aria-label="Toggle narration audio"
        >
          <span>${this.isPlayingAudio ? '⏸️' : '▶️'}</span>
          <span>${this.isPlayingAudio ? 'Pause Narration' : 'Play Narration'}</span>
        </button>

        <div class="audio-info">
          <div class="audio-title">The Watcher Audio Chronicle</div>
          <div class="audio-subtitle">
            ${this.isPlayingAudio ? 'Streaming voice synthesis...' : 'Ready to recite'}
          </div>
        </div>

        ${this.isPlayingAudio
          ? html`
              <div class="audio-waveform" aria-hidden="true">
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
              </div>
            `
          : ''}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-absentee-recap': RunefobleAbsenteeRecap;
  }
}
