/**
 * Standalone Lit Web Component for Kinetic 3D Dice Tray & Audio (TASK-0170).
 * High-performance polyhedral dice rendering, synchronized WebAudio tray clatter,
 * and 100% cryptographic roll outcome alignment.
 */

import { LitElement, html } from 'lit';
import { customElement, property, query } from 'lit/decorators.js';
import { type DiceType, DICE_CONFIGS, getPolyhedralVertices, getDiceColors } from './physics_3d/dice_models.ts';
import { DiceTrayAudio, type ImpactType } from './physics_3d/tray_audio.ts';
import { solveDeterministicToss, type SolvedDiceToss, type DiceTossParams } from './physics_3d/dice_solver.ts';
import { diceTrayStyles } from './runefoble-dice-tray-3d.styles.ts';

interface ActiveDieAnim {
  solved: SolvedDiceToss;
  startTime: number;
  lastCollisionIdx: number;
  settled: boolean;
}

@customElement('runefoble-dice-tray-3d')
export class RunefobleDiceTray3D extends LitElement {
  static styles = diceTrayStyles;

  @property({ type: String }) theme: 'dark' | 'light' | 'high-contrast' = 'dark';
  @property({ type: Boolean }) muted = false;
  @property({ type: Number }) width = 480;
  @property({ type: Number }) height = 280;

  @query('canvas') private canvasElement!: HTMLCanvasElement;
  public audio = new DiceTrayAudio();
  private activeRolls: ActiveDieAnim[] = [];
  private animId: number | null = null;
  public lastSettled: SolvedDiceToss | null = null;

  firstUpdated() {
    this.audio.onImpact = (type: ImpactType, vel: number) => {
      this.dispatchEvent(new CustomEvent('tray-audio-played', {
        detail: { impactType: type, velocity: vel }, bubbles: true, composed: true,
      }));
    };
    const render = () => {
      this.updateSimulation();
      this.drawCanvas();
      this.animId = requestAnimationFrame(render);
    };
    this.animId = requestAnimationFrame(render);
  }

  updated(changed: Map<string, any>) {
    if (changed.has('muted')) this.audio.setMuted(this.muted);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.animId) cancelAnimationFrame(this.animId);
    this.audio.close();
  }

  public roll(diceType: DiceType = 'd20', targetFace?: number, opts?: Partial<DiceTossParams>): SolvedDiceToss {
    const sides = DICE_CONFIGS[diceType]?.sides ?? 20;
    const face = targetFace ?? Math.floor(Math.random() * sides) + 1;
    const solved = solveDeterministicToss({
      diceType, targetFaceValue: face,
      origin: opts?.origin ?? { x: 1.0, y: 1.0, z: 3.5 },
      velocity: opts?.velocity ?? { x: 5.5, y: 4.8, z: 1.8 },
      trayBounds: { minX: 0.8, maxX: 7.2, minY: 0.8, maxY: 4.2 },
      seed: opts?.seed, diceId: opts?.diceId,
    });
    this.activeRolls.push({ solved, startTime: performance.now(), lastCollisionIdx: -1, settled: false });
    this.dispatchEvent(new CustomEvent('dice-rolled', {
      detail: { diceId: solved.diceId, diceType, targetFaceValue: face }, bubbles: true, composed: true,
    }));
    return solved;
  }

  public rollMultiple(rolls: Array<{ diceType: DiceType; targetFaceValue?: number }>): SolvedDiceToss[] {
    return rolls.map((r, i) => this.roll(r.diceType, r.targetFaceValue, { origin: { x: 1.0 + i * 0.5, y: 1.0, z: 3.5 + i * 0.2 } }));
  }

  public clear(): void { this.activeRolls = []; this.lastSettled = null; this.requestUpdate(); }

  private updateSimulation() {
    const now = performance.now();
    for (const roll of this.activeRolls) {
      if (roll.settled) continue;
      const elapsed = (now - roll.startTime) / 1000;
      for (let i = roll.lastCollisionIdx + 1; i < roll.solved.collisions.length; i++) {
        const col = roll.solved.collisions[i];
        if (elapsed >= col.t) {
          this.audio.playImpact({ impactType: col.type, velocity: Math.sqrt(col.energy * 2) });
          roll.lastCollisionIdx = i;
        } else break;
      }
      if (elapsed >= roll.solved.duration) {
        roll.settled = true;
        this.lastSettled = roll.solved;
        this.audio.playSettle(roll.solved.faceValue, roll.solved.faceValue === DICE_CONFIGS[roll.solved.diceType].sides);
        this.dispatchEvent(new CustomEvent('dice-settled', {
          detail: roll.solved, bubbles: true, composed: true,
        }));
        this.requestUpdate();
      }
    }
  }

  private drawCanvas() {
    if (!this.canvasElement) return;
    const ctx = this.canvasElement.getContext('2d');
    if (!ctx) return;
    const w = (this.canvasElement.width = this.width), h = (this.canvasElement.height = this.height);
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = this.theme === 'light' ? '#cbd5e1' : '#0f172a';
    ctx.fillRect(0, 0, w, h);

    const now = performance.now();
    for (const roll of this.activeRolls) {
      const elapsed = (now - roll.startTime) / 1000, traj = roll.solved.trajectory;
      const stepIdx = Math.min(traj.length - 1, Math.floor((elapsed / roll.solved.duration) * (traj.length - 1)));
      const pt = traj[Math.max(0, stepIdx)] || traj[traj.length - 1];
      const px = pt.x * (w / 8), py = pt.y * (h / 5) - pt.z * 18;
      const size = DICE_CONFIGS[roll.solved.diceType].radius * (1 + pt.z * 0.12);
      const palette = getDiceColors(roll.solved.diceType, roll.solved.faceValue, this.theme);

      ctx.save(); ctx.translate(px, py); ctx.rotate(pt.rotZ);
      ctx.beginPath();
      const poly = getPolyhedralVertices(roll.solved.diceType, size);
      poly.forEach(([vx, vy], i) => (i === 0 ? ctx.moveTo(vx, vy) : ctx.lineTo(vx, vy)));
      ctx.closePath();
      ctx.fillStyle = palette.bg; ctx.fill();
      ctx.strokeStyle = palette.border; ctx.lineWidth = palette.isCrit ? 2.5 : 1.5; ctx.stroke();
      ctx.fillStyle = palette.text; ctx.font = `bold ${Math.round(size * 0.85)}px monospace`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(`${roll.solved.faceValue}`, 0, 1);
      ctx.restore();
    }
  }

  render() {
    return html`
      <canvas width="${this.width}" height="${this.height}"></canvas>
      <div class="tray-hud">
        ${this.lastSettled ? html`<span class="result-badge">🎲 ${this.lastSettled.diceType.toUpperCase()}: ${this.lastSettled.faceValue}</span>` : html`<span></span>`}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap { 'runefoble-dice-tray-3d': RunefobleDiceTray3D; }
}
