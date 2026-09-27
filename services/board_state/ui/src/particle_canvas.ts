/**
 * WebGL Particle Visual Effects Engine for tactical board magic and kinetic spells.
 * Features 60fps lightweight instanced rendering, ephemeral grid decals, and theme bloom calibration.
 */

import {
  createAbjurationShieldParticles,
  createArchetypeParticles,
  createConjurationPortalParticles,
  createFirestormParticles,
  createFrostBloomParticles,
  createLightningArcParticles,
} from './particle_archetypes.ts';
import {
  drawInstancedParticles,
  initWebGLProgram,
  PARTICLE_ATTRIB_CONFIGS,
  PARTICLE_FRAGMENT_SHADER,
  PARTICLE_VERTEX_SHADER,
} from './particle_shaders.ts';
import type {
  EphemeralDecal,
  Particle,
  ParticleEngineOptions,
  SpellArchetype,
  SpellVFXParams,
  VFXThemeMode,
} from './particle_types.ts';
import { createActiveProjectile, ProjectileManager } from './particle_projectiles.ts';
import { DecalManager } from './particle_decals.ts';

export * from './particle_archetypes.ts';
export * from './particle_shaders.ts';
export * from './particle_types.ts';
export * from './particle_projectiles.ts';
export * from './particle_decals.ts';

export class WebGLParticleEngine {
  private canvas: HTMLCanvasElement;
  private gl: WebGLRenderingContext | null = null;
  private ctx2d: CanvasRenderingContext2D | null = null;
  private program: WebGLProgram | null = null;
  private particles: Particle[] = [];
  private projectileManager = new ProjectileManager();
  private decalManager = new DecalManager();
  private cellSizePx: number;
  private cols: number;
  private rows: number;
  private maxParticles: number;
  private themeMode: VFXThemeMode = 'dark';
  private bloomIntensity = 1.4;
  private isRunning = false;
  private animFrameId: number | null = null;
  private lastTimestamp = 0;
  private quadBuffer: WebGLBuffer | null = null;
  private instancedBuffer: WebGLBuffer | null = null;
  private attribLocations: Record<string, number> = {};
  private uniformLocations: Record<string, WebGLUniformLocation | null> = {};

  constructor(canvas: HTMLCanvasElement, options: ParticleEngineOptions = {}) {
    this.canvas = canvas;
    this.cellSizePx = options.cellSizePx ?? 54;
    this.cols = options.cols ?? 8;
    this.rows = options.rows ?? 8;
    this.maxParticles = options.maxParticles ?? 800;
    this.setThemeMode(options.themeMode ?? 'dark');
    this.initContext();
    this.start();
  }

  private initContext(): void {
    try { this.gl = this.canvas.getContext('webgl', { alpha: true, antialias: true }); } catch { this.gl = null; }
    if (this.gl) { this.initWebGL(); } else {
      try { this.ctx2d = this.canvas.getContext('2d'); } catch { this.ctx2d = null; }
    }
  }

  private initWebGL(): void {
    const gl = this.gl;
    if (!gl) return;
    this.program = initWebGLProgram(gl, PARTICLE_VERTEX_SHADER, PARTICLE_FRAGMENT_SHADER);
    if (!this.program || !gl.isProgram(this.program)) { this.gl = null; return; }

    gl.useProgram(this.program);
    this.quadBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
    this.instancedBuffer = gl.createBuffer();

    this.attribLocations = { quadPos: gl.getAttribLocation(this.program, 'a_quad_pos') };
    for (const [k, attr] of PARTICLE_ATTRIB_CONFIGS) {
      this.attribLocations[k] = gl.getAttribLocation(this.program, attr);
    }
    this.uniformLocations = {
      resolution: gl.getUniformLocation(this.program, 'u_resolution'),
      bloomIntensity: gl.getUniformLocation(this.program, 'u_bloom_intensity'),
      themeMode: gl.getUniformLocation(this.program, 'u_theme_mode'),
    };
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
  }

  public setThemeMode(mode: VFXThemeMode): void {
    this.themeMode = mode;
    this.bloomIntensity = mode === 'light' ? 1.0 : mode === 'high-contrast' ? 1.3 : 1.5;
    if (this.gl && this.program && this.uniformLocations.bloomIntensity) {
      this.gl.useProgram(this.program);
      this.gl.uniform1f(this.uniformLocations.bloomIntensity, this.bloomIntensity);
      if (this.uniformLocations.themeMode) {
        this.gl.uniform1i(this.uniformLocations.themeMode, mode === 'light' ? 1 : mode === 'high-contrast' ? 2 : 0);
      }
    }
  }

  public getGridDimensions(): { cols: number; rows: number } { return { cols: this.cols, rows: this.rows }; }
  public getThemeMode(): VFXThemeMode { return this.themeMode; }

  public resize(width: number, height: number): void {
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    if (this.gl && this.program && this.uniformLocations.resolution) {
      this.gl.viewport(0, 0, width, height);
      this.gl.useProgram(this.program);
      this.gl.uniform2f(this.uniformLocations.resolution, width, height);
    }
  }

  public triggerSpellVFX(params: SpellVFXParams): void {
    const archetype: SpellArchetype = params.spellArchetype ?? 'evocation';
    const targetPx = this.gridToPixel(params.toX, params.toY);
    const hasOrigin = params.fromX !== undefined && params.fromY !== undefined && (params.fromX !== params.toX || params.fromY !== params.toY);

    if (hasOrigin && archetype !== 'abjuration') {
      const startPx = this.gridToPixel(params.fromX!, params.fromY!);
      this.projectileManager.add(createActiveProjectile(params, startPx, targetPx, this.cellSizePx, () => {
        this.explodeArchetype(archetype, targetPx.x, targetPx.y, params);
        params.onImpact?.();
      }));
    } else {
      this.explodeArchetype(archetype, targetPx.x, targetPx.y, params);
      params.onImpact?.();
      if (params.onFinish) setTimeout(params.onFinish, archetype === 'abjuration' ? 650 : 500);
    }
  }

  private explodeArchetype(archetype: SpellArchetype, cx: number, cy: number, params: SpellVFXParams): void {
    const { particles, decalType } = createArchetypeParticles(archetype, cx, cy, params.spellName, params.damageType);
    this.particles.push(...particles);
    this.decalManager.add(params.toX, params.toY, decalType, 2);
  }

  public spawnFirestorm(cx: number, cy: number, count = 75): void { this.particles.push(...createFirestormParticles(cx, cy, count)); }
  public spawnLightningArc(cx: number, cy: number): void { this.particles.push(...createLightningArcParticles(cx, cy)); }
  public spawnAbjurationShield(cx: number, cy: number): void { this.particles.push(...createAbjurationShieldParticles(cx, cy)); }
  public spawnConjurationPortal(cx: number, cy: number): void { this.particles.push(...createConjurationPortalParticles(cx, cy)); }
  public spawnFrostBloom(cx: number, cy: number): void { this.particles.push(...createFrostBloomParticles(cx, cy)); }

  public decayDecals(rounds = 1): EphemeralDecal[] { return this.decalManager.decay(rounds); }
  public getDecals(): EphemeralDecal[] { return this.decalManager.getDecals(); }
  public getActiveParticlesCount(): number { return this.particles.length; }
  public getActiveProjectilesCount(): number { return this.projectileManager.count; }

  public start(): void {
    if (this.isRunning) return;
    this.isRunning = true;
    this.lastTimestamp = performance.now();
    this.loop(this.lastTimestamp);
  }

  public stop(): void {
    this.isRunning = false;
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
  }

  public dispose(): void {
    this.stop();
    this.particles = [];
    this.projectileManager.clear();
    this.decalManager.clear();
    if (this.gl) {
      if (this.quadBuffer) this.gl.deleteBuffer(this.quadBuffer);
      if (this.instancedBuffer) this.gl.deleteBuffer(this.instancedBuffer);
      if (this.program) this.gl.deleteProgram(this.program);
    }
  }

  private loop(now: number): void {
    if (!this.isRunning) return;
    const deltaMs = Math.min(50, now - (this.lastTimestamp || now));
    this.lastTimestamp = now;
    this.update(deltaMs);
    this.render();
    this.animFrameId = requestAnimationFrame((t) => this.loop(t));
  }

  public update(deltaMs: number): void {
    const dtSec = deltaMs / 1000;
    this.projectileManager.update(deltaMs, (p) => this.particles.push(p));

    for (let i = this.particles.length - 1; i >= 0; i--) {
      const pt = this.particles[i];
      pt.age += dtSec;
      pt.life = Math.max(0, 1.0 - pt.age / pt.maxLife);
      pt.x += pt.vx;
      pt.y += pt.vy;
      pt.rotation += pt.rotationSpeed;
      pt.size = pt.initialSize * pt.life;
      if (pt.life <= 0) this.particles.splice(i, 1);
    }

    if (this.particles.length > this.maxParticles) {
      this.particles.splice(0, this.particles.length - this.maxParticles);
    }
  }

  public render(): void {
    if (this.gl && this.program) this.renderWebGL();
    else if (this.ctx2d) this.render2DFallback();
  }

  private renderWebGL(): void {
    const gl = this.gl!;
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    if (!this.particles.length || !this.program || !this.quadBuffer || !this.instancedBuffer) return;
    drawInstancedParticles(gl, this.program, this.quadBuffer, this.instancedBuffer, this.attribLocations, this.particles);
  }

  private render2DFallback(): void {
    const ctx = this.ctx2d!;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.decalManager.render2D(ctx, this.cellSizePx);
    for (const p of this.particles) {
      ctx.save();
      ctx.beginPath();
      ctx.arc(p.x, p.y, Math.max(1, p.size), 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${Math.round(p.color[0] * 255)}, ${Math.round(p.color[1] * 255)}, ${Math.round(p.color[2] * 255)}, ${p.color[3] * p.life})`;
      ctx.fill();
      ctx.restore();
    }
  }

  private gridToPixel(gridX: number, gridY: number): { x: number; y: number } {
    return {
      x: gridX * this.cellSizePx + this.cellSizePx / 2,
      y: gridY * this.cellSizePx + this.cellSizePx / 2,
    };
  }
}
