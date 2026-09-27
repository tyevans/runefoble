/**
 * Tabletop 3D WebGL & Physics Visualizer Canvas.
 * Renders 3D miniature tokens, physical tumbling dice, elevation cliffs,
 * and knockback impact collisions on the tactical board.
 */

import {
  type Camera3D,
  type Miniature3DToken,
  project3D,
  renderElevationCliff,
  renderMiniatureBase,
} from './miniature_mesh.ts';

export interface DiceRollAnim {
  diceId: string; diceType: string; faceValue: number;
  trajectory: Array<{ x: number; y: number; z: number }>;
  settledCell: [number, number]; progress: number; rot: number; settled: boolean;
}

export interface KnockbackAnim {
  tokenId: string; fromX: number; fromY: number; toX: number; toY: number;
  progress: number; collided: boolean; collisionType?: string; impactEnergy: number; settled: boolean;
}

export class TabletopPhysicsVisualizer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D | null = null;
  private animId: number | null = null;
  private isRunning = false;
  private lastTime = 0;
  private tokens: Miniature3DToken[] = [];
  private terrain: Array<{ x: number; y: number; elevation?: number }> = [];
  private activeDice: DiceRollAnim[] = [];
  private activeKnockbacks: KnockbackAnim[] = [];
  public cellSizePx = 54;
  public cols = 8; public rows = 8;
  public theme: 'dark' | 'light' | 'high-contrast' = 'dark';
  public camera: Camera3D = { rotX: 42, rotY: 0, zoom: 0.95 };

  constructor(canvas: HTMLCanvasElement, opts?: { cellSizePx?: number; cols?: number; rows?: number; theme?: 'dark' | 'light' | 'high-contrast' }) {
    this.canvas = canvas;
    if (opts?.cellSizePx) this.cellSizePx = opts.cellSizePx;
    if (opts?.cols) this.cols = opts.cols;
    if (opts?.rows) this.rows = opts.rows;
    if (opts?.theme) this.theme = opts.theme;
    this.ctx = canvas.getContext('2d');
    this.start();
  }

  public updateTokens(tokens: Miniature3DToken[]): void { this.tokens = [...tokens]; }
  public updateTerrain(cells: Array<{ x: number; y: number; elevation?: number }>): void { this.terrain = [...cells]; }
  public setTheme(theme: 'dark' | 'light' | 'high-contrast'): void { this.theme = theme; }

  public rollDice(dice: { diceId?: string; diceType?: string; faceValue: number; settledCell: [number, number]; trajectory?: Array<{ x: number; y: number; z: number }> }): void {
    const traj = dice.trajectory?.length ? dice.trajectory : [
      { x: 1, y: 1, z: 3 }, { x: (dice.settledCell[0] + 1) / 2, y: (dice.settledCell[1] + 1) / 2, z: 1.5 },
      { x: dice.settledCell[0], y: dice.settledCell[1], z: 0.1 },
    ];
    this.activeDice.push({
      diceId: dice.diceId || `dice-${Date.now()}`, diceType: dice.diceType || 'd20',
      faceValue: dice.faceValue, trajectory: traj, settledCell: dice.settledCell,
      progress: 0, rot: 0, settled: false,
    });
  }

  public knockbackToken(kb: { tokenId: string; fromX: number; fromY: number; toX: number; toY: number; collided?: boolean; collisionType?: string; impactEnergy?: number }): void {
    this.activeKnockbacks.push({
      tokenId: kb.tokenId, fromX: kb.fromX, fromY: kb.fromY, toX: kb.toX, toY: kb.toY,
      progress: 0, collided: Boolean(kb.collided), collisionType: kb.collisionType,
      impactEnergy: kb.impactEnergy ?? 0, settled: false,
    });
  }

  public start(): void {
    if (this.isRunning) return;
    this.isRunning = true;
    this.lastTime = performance.now();
    const loop = (t: number) => {
      if (!this.isRunning) return;
      this.update((t - this.lastTime) / 1000);
      this.lastTime = t;
      this.render();
      this.animId = requestAnimationFrame(loop);
    };
    this.animId = requestAnimationFrame(loop);
  }

  public stop(): void { this.isRunning = false; if (this.animId) cancelAnimationFrame(this.animId); }
  public dispose(): void { this.stop(); this.activeDice = []; this.activeKnockbacks = []; }

  public update(dt: number): void {
    for (const d of this.activeDice) {
      if (!d.settled) {
        d.progress = Math.min(1, d.progress + dt * 1.4);
        d.rot += dt * 12;
        if (d.progress >= 1) d.settled = true;
      }
    }
    for (const k of this.activeKnockbacks) {
      if (!k.settled) {
        k.progress = Math.min(1, k.progress + dt * 2.2);
        if (k.progress >= 1) k.settled = true;
      }
    }
  }

  public render(): void {
    const ctx = this.ctx;
    if (!ctx) return;
    const w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);
    const ox = this.cols / 2, oy = this.rows / 2;

    // 1. Render Elevation Cliffs
    for (const c of this.terrain) {
      if ((c.elevation ?? 0) > 0) {
        const pt = project3D(c.x + 0.5, c.y + 0.5, 0, this.cellSizePx, this.camera, ox, oy);
        renderElevationCliff(ctx, { x: w / 2 + pt.px, y: h / 2 + pt.py }, c.elevation!, this.cellSizePx, this.camera.zoom);
      }
    }

    // 2. Render 3D Miniature Tokens
    for (const t of this.tokens) {
      const kb = this.activeKnockbacks.find((k) => k.tokenId === t.id && !k.settled);
      const curX = kb ? t.x + (kb.toX - kb.fromX) * kb.progress : t.x;
      const curY = kb ? t.y + (kb.toY - kb.fromY) * kb.progress : t.y;
      const tilt = kb ? Math.sin(kb.progress * Math.PI) * 0.45 : 0;
      const cellElev = this.terrain.find((c) => c.x === Math.round(curX) && c.y === Math.round(curY))?.elevation ?? 0;
      const pt = project3D(curX + 0.5, curY + 0.5, cellElev, this.cellSizePx, this.camera, ox, oy);
      renderMiniatureBase(ctx, { x: w / 2 + pt.px, y: h / 2 + pt.py }, { ...t, tiltAngleX: tilt }, 21 * this.camera.zoom);
    }

    // 3. Render Tumbling Physical Dice
    for (const d of this.activeDice) {
      const idx = Math.min(d.trajectory.length - 1, Math.floor(d.progress * (d.trajectory.length - 1)));
      const step = d.trajectory[idx] || { x: d.settledCell[0], y: d.settledCell[1], z: 0 };
      const pt = project3D(step.x + 0.5, step.y + 0.5, step.z, this.cellSizePx, this.camera, ox, oy);
      this.renderDie(ctx, w / 2 + pt.px, h / 2 + pt.py, d);
    }
  }

  private renderDie(ctx: CanvasRenderingContext2D, px: number, py: number, d: DiceRollAnim): void {
    ctx.save();
    ctx.translate(px, py);
    ctx.rotate(d.settled ? 0 : d.rot);
    const size = 18 * this.camera.zoom;
    // Die shadow
    ctx.beginPath();
    ctx.ellipse(2, 6, size * 0.8, size * 0.4, 0, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
    ctx.fill();

    // Polyhedral Die Body
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = (i * Math.PI) / 3;
      const dx = Math.cos(a) * size, dy = Math.sin(a) * size;
      if (i === 0) ctx.moveTo(dx, dy); else ctx.lineTo(dx, dy);
    }
    ctx.closePath();
    ctx.fillStyle = d.faceValue === 20 ? '#fbbf24' : '#b91c1c';
    ctx.fill();
    ctx.strokeStyle = '#fef08a';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Resting Face Numeral
    ctx.fillStyle = '#ffffff';
    ctx.font = `bold ${Math.round(11 * this.camera.zoom)}px monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${d.faceValue}`, 0, 1);
    ctx.restore();
  }
}
