import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface LiarDicePlayer {
  id: string;
  name: string;
  diceCount: number;
}

@customElement('runefoble-minigame-liars-dice')
export class RunefobleMinigameLiarsDice extends LitElement {
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
    .cup-tray {
      position: relative;
      background: #0f172a;
      border: 2px solid #334155;
      border-radius: 8px;
      height: 150px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      margin-bottom: 12px;
      cursor: grab;
    }
    .cup-tray.shaking {
      animation: cup-rattle 0.3s infinite alternate ease-in-out;
    }
    @keyframes cup-rattle {
      0% { transform: translate(-3px, 2px) rotate(-2deg); }
      100% { transform: translate(3px, -2px) rotate(2deg); }
    }
    .dice-row {
      display: flex;
      gap: 8px;
      z-index: 1;
    }
    .die {
      width: 40px;
      height: 40px;
      background: #f8fafc;
      color: #0f172a;
      border-radius: 6px;
      font-size: 1.3rem;
      font-weight: 900;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 2px solid #cbd5e1;
      box-shadow: 2px 2px 0px #000;
    }
    .die.wild { border-color: #f59e0b; color: #d97706; }
    .peek-shade {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: #334155;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2;
      transition: transform 0.25s ease-out;
      font-size: 0.85rem;
      font-weight: 700;
      color: #94a3b8;
    }
    .peek-shade.peeking { transform: translateY(-75%); }
    .hud {
      display: flex;
      justify-content: space-between;
      margin-bottom: 12px;
      font-size: 0.8rem;
    }
    .bid-controls {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 12px;
    }
    .btn {
      background: var(--rf-accent, #3b82f6);
      color: #fff;
      border: 2px solid #0f172a;
      padding: 8px 12px;
      font-weight: 700;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.85rem;
    }
    .btn.bluff { background: #ef4444; }
    .btn:active { transform: translateY(1px); }
    .players-list {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding: 6px 0;
      border-top: 1px solid #334155;
    }
    .player-pill {
      background: #0f172a;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      white-space: nowrap;
      border: 1px solid #475569;
    }
    .player-pill.out { opacity: 0.4; text-decoration: line-through; }
  `;

  @property({ type: Array }) myDice: number[] = [2, 3, 3, 5, 6];
  @property({ type: Object }) currentBid: { quantity: number; face: number; bidder: string } | null = null;
  @property({ type: Array }) players: LiarDicePlayer[] = [
    { id: 'player-1', name: 'You', diceCount: 5 },
    { id: 'player-2', name: 'Grimjaw', diceCount: 4 },
    { id: 'player-3', name: 'Sylvia', diceCount: 3 },
  ];
  @property({ type: Number }) pot = 50;

  @state() private isShaking = false;
  @state() private isPeeking = false;
  @state() private bidQty = 2;
  @state() private bidFace = 3;

  private triggerHaptic() {
    if (typeof navigator !== 'undefined' && navigator.vibrate) {
      navigator.vibrate([20, 40, 20]);
    }
  }

  private playShakeAudio() {
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      for (let i = 0; i < 4; i++) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.frequency.setValueAtTime(180 + Math.random() * 80, ctx.currentTime + i * 0.04);
        gain.gain.setValueAtTime(0.3, ctx.currentTime + i * 0.04);
        gain.gain.linearRampToValueAtTime(0, ctx.currentTime + i * 0.04 + 0.05);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime + i * 0.04);
        osc.stop(ctx.currentTime + i * 0.04 + 0.05);
      }
    } catch {}
  }

  public shakeCup() {
    if (this.isShaking) return;
    this.isShaking = true;
    this.triggerHaptic();
    this.playShakeAudio();
    setTimeout(() => {
      this.myDice = Array.from({ length: this.myDice.length }, () => Math.floor(Math.random() * 6) + 1).sort();
      this.isShaking = false;
      this.dispatchEvent(new CustomEvent('dice-shaken', {
        detail: { dice: this.myDice },
        bubbles: true, composed: true,
      }));
    }, 450);
  }

  public placeBid() {
    const bid = { quantity: this.bidQty, face: this.bidFace, bidder: 'You' };
    this.currentBid = bid;
    this.dispatchEvent(new CustomEvent('bid-placed', {
      detail: bid,
      bubbles: true, composed: true,
    }));
  }

  public callLiar() {
    this.isPeeking = true;
    this.dispatchEvent(new CustomEvent('liar-called', {
      detail: { challenger: 'You', targetBid: this.currentBid },
      bubbles: true, composed: true,
    }));
  }

  render() {
    return html`
      <div class="hud">
        <span>Pot: <strong style="color:#f59e0b;">${this.pot} gp</strong></span>
        <span>
          ${this.currentBid
            ? html`Active Bid: <strong>${this.currentBid.quantity}x [${this.currentBid.face}]</strong> by ${this.currentBid.bidder}`
            : 'No active bid'}
        </span>
      </div>

      <div class="cup-tray ${this.isShaking ? 'shaking' : ''}"
           @click=${this.shakeCup}
           @pointerdown=${() => { this.isPeeking = true; }}
           @pointerup=${() => { this.isPeeking = false; }}>
        <div class="dice-row">
          ${this.myDice.map(d => html`
            <div class="die ${d === 1 ? 'wild' : ''}">${d}</div>
          `)}
        </div>
        <div class="peek-shade ${this.isPeeking ? 'peeking' : ''}">
          🔒 Press & Hold to Peek Cup (Swipe to Shake)
        </div>
      </div>

      <div class="bid-controls">
        <div style="display:flex; gap:4px; align-items:center;">
          <label style="font-size:0.75rem;">Qty:</label>
          <input type="number" min="1" max="20" .value=${String(this.bidQty)}
                 @change=${(e: Event) => { this.bidQty = parseInt((e.target as HTMLInputElement).value, 10); }}
                 style="width:50px; background:#0f172a; color:#fff; border:1px solid #475569; padding:4px;" />
          <label style="font-size:0.75rem;">Face:</label>
          <select .value=${String(this.bidFace)}
                  @change=${(e: Event) => { this.bidFace = parseInt((e.target as HTMLSelectElement).value, 10); }}
                  style="background:#0f172a; color:#fff; border:1px solid #475569; padding:4px;">
            ${[1, 2, 3, 4, 5, 6].map(f => html`<option value="${f}">${f}${f === 1 ? ' (★)' : ''}</option>`)}
          </select>
        </div>
        <div style="display:flex; gap:6px;">
          <button class="btn" @click=${this.placeBid} style="flex:1;">Bid</button>
          <button class="btn bluff" @click=${this.callLiar} style="flex:1;">Liar!</button>
        </div>
      </div>

      <div class="players-list">
        ${this.players.map(p => html`
          <div class="player-pill ${p.diceCount <= 0 ? 'out' : ''}">
            ${p.name}: ${p.diceCount > 0 ? `${p.diceCount} 🎲` : 'Eliminated'}
          </div>
        `)}
      </div>
    `;
  }
}
