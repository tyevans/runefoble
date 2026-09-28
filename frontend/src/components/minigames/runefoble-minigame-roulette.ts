import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface RouletteBet {
  type: 'straight' | 'color' | 'even_odd';
  target: number | string;
  amount: number;
  player: string;
}

const RED_NUMS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];

@customElement('runefoble-minigame-roulette')
export class RunefobleMinigameRoulette extends LitElement {
  static styles = css`
    :host {
      display: block;
      box-sizing: border-box;
      max-width: 420px;
      margin: 0 auto;
      background: var(--rf-surface, #1e293b);
      color: var(--rf-text-primary, #f8fafc);
      border: 3px solid var(--rf-border-color, #0f172a);
      border-radius: 8px;
      padding: 16px;
      font-family: var(--rf-font-family, system-ui, sans-serif);
      user-select: none;
    }
    .wheel-area {
      display: flex;
      flex-direction: column;
      align-items: center;
      margin-bottom: 12px;
    }
    .wheel-disc {
      width: 140px;
      height: 140px;
      border-radius: 50%;
      border: 6px solid #b45309;
      background: conic-gradient(
        #22c55e 0deg 9.7deg,
        #ef4444 9.7deg 19.4deg, #0f172a 19.4deg 29.1deg,
        #ef4444 29.1deg 38.8deg, #0f172a 38.8deg 48.5deg,
        #ef4444 48.5deg 58.2deg, #0f172a 58.2deg 67.9deg,
        #ef4444 67.9deg 77.6deg, #0f172a 77.6deg 87.3deg,
        #ef4444 87.3deg 97.0deg, #0f172a 97.0deg 106.7deg,
        #ef4444 106.7deg 116.4deg, #0f172a 116.4deg 126.1deg,
        #ef4444 126.1deg 135.8deg, #0f172a 135.8deg 145.5deg,
        #ef4444 145.5deg 155.2deg, #0f172a 155.2deg 164.9deg,
        #ef4444 164.9deg 174.6deg, #0f172a 174.6deg 184.3deg,
        #ef4444 184.3deg 194.0deg, #0f172a 194.0deg 203.7deg,
        #ef4444 203.7deg 213.4deg, #0f172a 213.4deg 223.1deg,
        #ef4444 223.1deg 232.8deg, #0f172a 232.8deg 242.5deg,
        #ef4444 242.5deg 252.2deg, #0f172a 252.2deg 261.9deg,
        #ef4444 261.9deg 271.6deg, #0f172a 271.6deg 281.3deg,
        #ef4444 281.3deg 291.0deg, #0f172a 291.0deg 300.7deg,
        #ef4444 300.7deg 310.4deg, #0f172a 310.4deg 320.1deg,
        #ef4444 320.1deg 329.8deg, #0f172a 329.8deg 339.5deg,
        #ef4444 339.5deg 349.2deg, #0f172a 349.2deg 360deg
      );
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: inset 0 0 10px #000;
      transition: transform 3s cubic-bezier(0.15, 0.9, 0.25, 1);
    }
    .wheel-hub {
      width: 44px;
      height: 44px;
      background: #78350f;
      border-radius: 50%;
      border: 3px solid #fef08a;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 900;
      color: #fff;
      font-size: 1.1rem;
    }
    .felt-table {
      background: #064e3b;
      border: 3px solid #047857;
      border-radius: 8px;
      padding: 8px;
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 4px;
      margin-bottom: 12px;
    }
    .felt-cell {
      height: 38px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      border: 1px solid #10b981;
      border-radius: 4px;
      cursor: pointer;
      font-weight: 700;
      font-size: 0.8rem;
      position: relative;
    }
    .felt-cell.red { background: #b91c1c; }
    .felt-cell.black { background: #0f172a; }
    .felt-cell.green { background: #047857; grid-column: span 6; }
    .token-chip {
      position: absolute;
      top: 2px;
      right: 2px;
      background: #f59e0b;
      color: #000;
      border-radius: 50%;
      width: 16px;
      height: 16px;
      font-size: 0.6rem;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 900;
    }
    .bet-bar {
      display: flex;
      justify-content: space-between;
      gap: 6px;
      margin-bottom: 12px;
    }
    .btn-side {
      flex: 1;
      padding: 6px;
      font-weight: 800;
      border-radius: 4px;
      border: 2px solid #0f172a;
      cursor: pointer;
      font-size: 0.75rem;
      text-transform: uppercase;
    }
    .btn-red { background: #ef4444; color: #fff; }
    .btn-black { background: #0f172a; color: #fff; }
    .btn-spin {
      background: var(--rf-accent, #f59e0b);
      color: #000;
      font-weight: 900;
      font-size: 1rem;
      padding: 8px;
      width: 100%;
      border: 2px solid #0f172a;
      border-radius: 4px;
      cursor: pointer;
    }
  `;

  @property({ type: Array }) bets: RouletteBet[] = [];
  @property({ type: Number }) playerChips = 100;
  @property({ type: Number }) winningNumber: number | null = null;
  @property({ type: Boolean }) isSpinning = false;

  @state() private selectedChip = 5;
  @state() private wheelRotation = 0;

  private triggerHaptic() {
    if (typeof navigator !== 'undefined' && navigator.vibrate) {
      navigator.vibrate([15, 30, 15]);
    }
  }

  private playClickAudio() {
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.setValueAtTime(320, ctx.currentTime);
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.05);
    } catch {}
  }

  public placeBet(type: 'straight' | 'color' | 'even_odd', target: number | string) {
    if (this.isSpinning || this.playerChips < this.selectedChip) return;
    this.playerChips -= this.selectedChip;
    this.bets = [...this.bets, {
      type,
      target,
      amount: this.selectedChip,
      player: 'You',
    }];
    this.triggerHaptic();
    this.playClickAudio();
    this.dispatchEvent(new CustomEvent('bet-placed', {
      detail: { bets: this.bets, chipsRemaining: this.playerChips },
      bubbles: true, composed: true,
    }));
  }

  public spinWheel(fixedNumber?: number) {
    if (this.isSpinning || this.bets.length === 0) return;
    this.isSpinning = true;
    const finalNumber = fixedNumber !== undefined ? fixedNumber : Math.floor(Math.random() * 37);
    this.wheelRotation += 1440 + (finalNumber * (360 / 37));

    setTimeout(() => {
      this.winningNumber = finalNumber;
      this.isSpinning = false;
      this.triggerHaptic();

      // Resolve bets
      const isRed = RED_NUMS.includes(finalNumber);
      let winnings = 0;
      for (const b of this.bets) {
        if (b.type === 'straight' && b.target === finalNumber) winnings += b.amount * 36;
        if (b.type === 'color' && ((b.target === 'red' && isRed) || (b.target === 'black' && !isRed && finalNumber !== 0))) {
          winnings += b.amount * 2;
        }
      }
      this.playerChips += winnings;
      this.dispatchEvent(new CustomEvent('wheel-spun', {
        detail: { winningNumber: finalNumber, winnings, playerChips: this.playerChips },
        bubbles: true, composed: true,
      }));
      this.bets = [];
    }, 3000);
  }

  render() {
    return html`
      <div style="display:flex; justify-content:space-between; margin-bottom:8px; font-size:0.85rem;">
        <span>Chips: <strong style="color:#f59e0b;">${this.playerChips} gp</strong></span>
        <span>${this.winningNumber !== null ? `Result: ${this.winningNumber}` : 'Place Bets'}</span>
      </div>

      <div class="wheel-area">
        <div class="wheel-disc" style="transform: rotate(${this.wheelRotation}deg);">
          <div class="wheel-hub">${this.winningNumber ?? '✦'}</div>
        </div>
      </div>

      <div class="felt-table">
        <div class="felt-cell green" @click=${() => this.placeBet('straight', 0)}>
          0
          ${this.bets.filter(b => b.target === 0).length ? html`<span class="token-chip">●</span>` : ''}
        </div>
        ${[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(n => html`
          <div class="felt-cell ${RED_NUMS.includes(n) ? 'red' : 'black'}"
               @click=${() => this.placeBet('straight', n)}>
            ${n}
            ${this.bets.filter(b => b.target === n).length ? html`<span class="token-chip">●</span>` : ''}
          </div>
        `)}
      </div>

      <div class="bet-bar">
        <button class="btn-side btn-red" @click=${() => this.placeBet('color', 'red')}>Red (1:1)</button>
        <button class="btn-side btn-black" @click=${() => this.placeBet('color', 'black')}>Black (1:1)</button>
      </div>

      <button class="btn-spin" ?disabled=${this.isSpinning || this.bets.length === 0} @click=${() => this.spinWheel()}>
        ${this.isSpinning ? 'Wheel Spinning...' : 'SPIN WHEEL'}
      </button>
    `;
  }
}
