import { LitElement, html, css, PropertyValues } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';

const SECTORS = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5];

@customElement('runefoble-minigame-darts')
export class RunefobleMinigameDarts extends LitElement {
  static styles = css`
    :host {
      display: block; box-sizing: border-box; max-width: 420px; margin: 0 auto;
      background: var(--rf-surface, #1e293b); color: var(--rf-text-primary, #f8fafc);
      border: 3px solid var(--rf-border-color, #0f172a); border-radius: 8px; padding: 16px;
      font-family: var(--rf-font-family, system-ui, sans-serif); touch-action: none; user-select: none;
    }
    .hud {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 12px; padding: 8px 12px; background: var(--rf-bg-surface, #0f172a);
      border-radius: 6px; border: 1px solid #334155;
    }
    .score-badge { font-size: 1.5rem; font-weight: 900; color: var(--rf-accent, #f59e0b); }
    .canvas-container {
      position: relative; width: 100%; height: 320px; display: flex;
      justify-content: center; align-items: center; background: #090d16;
      border-radius: 6px; overflow: hidden; border: 2px solid #334155;
    }
    canvas { width: 320px; height: 320px; display: block; }
    .aim-overlay {
      position: absolute; bottom: 8px; font-size: 0.75rem; color: #94a3b8;
      pointer-events: none; text-transform: uppercase; letter-spacing: 0.05em;
    }
    .footer { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; gap: 8px; }
    .btn {
      background: var(--rf-accent, #3b82f6); color: #fff; border: 2px solid #0f172a;
      padding: 6px 12px; font-weight: 700; border-radius: 4px; cursor: pointer; font-size: 0.8rem;
    }
  `;

  @property({ type: String }) rulesMode: '501' | 'cricket' = '501';
  @property({ type: Number }) targetScore = 501;
  @property({ type: Number }) currentScore = 501;
  @property({ type: Array }) throwHistory: number[] = [];
  @property({ type: String }) lastHitText = 'Ready to throw';
  @property({ type: Boolean }) isGameOver = false;

  @state() private dragStart: { x: number; y: number; time: number } | null = null;
  @state() private currentPos: { x: number; y: number } | null = null;
  @state() private dartPos: { x: number; y: number } | null = null;

  @query('canvas') private canvas!: HTMLCanvasElement;

  firstUpdated(_changed: PropertyValues) {
    super.firstUpdated(_changed);
    this.renderDartboard();
  }

  private triggerHaptic() {
    if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate([15, 30, 15]);
  }

  private playImpactAudio() {
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(140, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(30, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(0.5, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.1);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.1);
    } catch {}
  }

  private renderDartboard() {
    if (!this.canvas) return;
    const ctx = this.canvas.getContext('2d');
    if (!ctx) return;
    const cx = 160, cy = 160, R = 140;
    ctx.clearRect(0, 0, 320, 320);

    ctx.fillStyle = '#0f172a';
    ctx.beginPath();
    ctx.arc(cx, cy, R + 10, 0, Math.PI * 2);
    ctx.fill();

    const step = (Math.PI * 2) / 20;
    for (let i = 0; i < 20; i++) {
      const angle = i * step - Math.PI / 2 - step / 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, R, angle, angle + step);
      ctx.fillStyle = i % 2 === 0 ? '#1e293b' : '#f8fafc';
      ctx.fill();

      // Triple & Double rings
      ctx.beginPath();
      ctx.arc(cx, cy, R * 0.62, angle, angle + step);
      ctx.arc(cx, cy, R * 0.55, angle + step, angle, true);
      ctx.fillStyle = i % 2 === 0 ? '#ef4444' : '#22c55e';
      ctx.fill();

      ctx.beginPath();
      ctx.arc(cx, cy, R, angle, angle + step);
      ctx.arc(cx, cy, R * 0.93, angle + step, angle, true);
      ctx.fillStyle = i % 2 === 0 ? '#ef4444' : '#22c55e';
      ctx.fill();
    }

    ctx.beginPath();
    ctx.arc(cx, cy, R * 0.12, 0, Math.PI * 2);
    ctx.fillStyle = '#22c55e';
    ctx.fill();
    ctx.beginPath();
    ctx.arc(cx, cy, R * 0.05, 0, Math.PI * 2);
    ctx.fillStyle = '#ef4444';
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 11px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (let i = 0; i < 20; i++) {
      const angle = i * step - Math.PI / 2;
      ctx.fillText(String(SECTORS[i]), cx + Math.cos(angle) * (R + 6), cy + Math.sin(angle) * (R + 6));
    }

    if (this.dartPos) {
      ctx.fillStyle = '#f59e0b';
      ctx.beginPath();
      ctx.arc(this.dartPos.x, this.dartPos.y, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }

  private handleTouchStart(e: TouchEvent | MouseEvent) {
    if (this.isGameOver) return;
    const pt = 'touches' in e ? e.touches[0] : e;
    const rect = this.canvas.getBoundingClientRect();
    this.dragStart = { x: pt.clientX - rect.left, y: pt.clientY - rect.top, time: Date.now() };
    this.currentPos = { ...this.dragStart };
  }

  private handleTouchMove(e: TouchEvent | MouseEvent) {
    if (!this.dragStart) return;
    const pt = 'touches' in e ? e.touches[0] : e;
    const rect = this.canvas.getBoundingClientRect();
    this.currentPos = { x: pt.clientX - rect.left, y: pt.clientY - rect.top };
  }

  private handleTouchEnd() {
    if (!this.dragStart || !this.currentPos) return;
    const dt = Math.max(15, Date.now() - this.dragStart.time);
    const dx = this.currentPos.x - this.dragStart.x;
    const dy = this.currentPos.y - this.dragStart.y;
    this.dragStart = null;
    this.currentPos = null;
    this.resolveThrow(-dx / (dt * 0.08), -dy / (dt * 0.08));
  }

  public resolveThrow(vx: number, vy: number) {
    const cx = 160, cy = 160;
    const tx = Math.max(20, Math.min(300, cx + vx * 2.2));
    const ty = Math.max(20, Math.min(300, cy + vy * 2.2));
    this.dartPos = { x: tx, y: ty };
    this.renderDartboard();
    this.triggerHaptic();
    this.playImpactAudio();

    const dist = Math.hypot(tx - cx, ty - cy);
    const angle = (Math.atan2(ty - cy, tx - cx) + Math.PI / 2 + Math.PI * 2) % (Math.PI * 2);
    let pts = 0;
    let label = 'Miss';

    if (dist <= 7) { pts = 50; label = 'Double Bull (50)'; }
    else if (dist <= 17) { pts = 25; label = 'Bullseye (25)'; }
    else if (dist <= 140) {
      const idx = Math.floor(((angle + (Math.PI / 20)) % (Math.PI * 2)) / (Math.PI / 10));
      const sector = SECTORS[idx % 20];
      if (dist >= 130 && dist <= 140) { pts = sector * 2; label = `Double ${sector} (${pts})`; }
      else if (dist >= 77 && dist <= 87) { pts = sector * 3; label = `Triple ${sector} (${pts})`; }
      else { pts = sector; label = `Single ${sector} (${pts})`; }
    }

    if (this.rulesMode === '501') {
      if (this.currentScore - pts === 0) {
        this.currentScore = 0; this.isGameOver = true; this.lastHitText = `WINNER! Hit ${label}`;
      } else if (this.currentScore - pts < 0) {
        this.lastHitText = `BUST! Hit ${label}`;
      } else {
        this.currentScore -= pts; this.lastHitText = `Hit ${label}`;
      }
    }
    this.throwHistory = [...this.throwHistory, pts];
    this.dispatchEvent(new CustomEvent('dart-thrown', {
      detail: { points: pts, remaining: this.currentScore, label },
      bubbles: true, composed: true,
    }));
  }

  public resetGame() {
    this.currentScore = this.targetScore;
    this.throwHistory = [];
    this.isGameOver = false;
    this.dartPos = null;
    this.lastHitText = 'Ready to throw';
    this.renderDartboard();
  }

  render() {
    return html`
      <div class="hud">
        <div>
          <span style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase;">501 Darts</span>
          <div class="score-badge">${this.currentScore}</div>
        </div>
        <div style="text-align:right;">
          <span style="font-size:0.75rem; color:#94a3b8;">Throws: ${this.throwHistory.length}</span>
          <div style="font-size:0.85rem; font-weight:700; color:#38bdf8;">${this.lastHitText}</div>
        </div>
      </div>
      <div class="canvas-container"
           @touchstart=${this.handleTouchStart}
           @touchmove=${this.handleTouchMove}
           @touchend=${this.handleTouchEnd}
           @mousedown=${this.handleTouchStart}
           @mousemove=${this.handleTouchMove}
           @mouseup=${this.handleTouchEnd}>
        <canvas width="320" height="320"></canvas>
        <div class="aim-overlay">Flick upward to throw</div>
      </div>
      <div class="footer">
        <button class="btn" @click=${this.resetGame}>New Leg</button>
        <span style="font-size:0.75rem; color:#94a3b8;">
          ${this.isGameOver ? '🏆 Match Finished!' : 'Touch flick gesture active'}
        </span>
      </div>
    `;
  }
}
