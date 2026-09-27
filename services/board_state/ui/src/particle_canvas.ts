/**
 * WebGL Particle Visual Effects Engine for tactical board magic and kinetic spells.
 * Features 60fps lightweight instanced rendering, ephemeral grid decals, and theme bloom calibration.
 */

import {
  createAbjurationShieldParticles,
  createConjurationPortalParticles,
  createFirestormParticles,
  createFrostBloomParticles,
  createLightningArcParticles,
  getArchetypeColor,
} from './particle_archetypes.ts';
import {
  initWebGLProgram,
  PARTICLE_FRAGMENT_SHADER,
  PARTICLE_VERTEX_SHADER,
} from './particle_shaders.ts';
import type {
  ActiveProjectile,
  DecalType,
  EphemeralDecal,
  Particle,
  ParticleEngineOptions,
  SpellArchetype,
  SpellVFXParams,
  VFXThemeMode,
} from './particle_types.ts';

export * from './particle_archetypes.ts';
export * from './particle_shaders.ts';
export * from './particle_types.ts';

export class WebGLParticleEngine {
  private canvas: HTMLCanvasElement;
  private gl: WebGLRenderingContext | null = null;
  private ctx2d: CanvasRenderingContext2D | null = null;
  private program: WebGLProgram | null = null;

  private particles: Particle[] = [];
  private projectiles: ActiveProjectile[] = [];
  private decals: EphemeralDecal[] = [];

  private cellSizePx: number;
  private cols: number;
  private rows: number;
  private maxParticles: number;
  private themeMode: VFXThemeMode = 'dark';
  private bloomIntensity = 1.4;


  private isRunning = false;
  private animFrameId: number | null = null;
  private lastTimestamp = 0;

  // WebGL Buffers & Attributes
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
    try {
      this.gl = this.canvas.getContext('webgl', { alpha: true, antialias: true });
    } catch {
      this.gl = null;
    }

    if (this.gl) {
      this.initWebGL();
    } else {
      try {
        this.ctx2d = this.canvas.getContext('2d');
      } catch {
        this.ctx2d = null;
      }
    }
  }

  private initWebGL(): void {
    const gl = this.gl;
    if (!gl) return;

    this.program = initWebGLProgram(gl, PARTICLE_VERTEX_SHADER, PARTICLE_FRAGMENT_SHADER);
    if (!programValid(gl, this.program)) {
      this.gl = null;
      return;
    }

    gl.useProgram(this.program);
    const quadVertices = new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]);
    this.quadBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, quadVertices, gl.STATIC_DRAW);

    this.instancedBuffer = gl.createBuffer();

    this.attribLocations = {
      quadPos: gl.getAttribLocation(this.program!, 'a_quad_pos'),
      particlePos: gl.getAttribLocation(this.program!, 'a_particle_pos'),
      color: gl.getAttribLocation(this.program!, 'a_color'),
      size: gl.getAttribLocation(this.program!, 'a_size'),
      life: gl.getAttribLocation(this.program!, 'a_life'),
      type: gl.getAttribLocation(this.program!, 'a_type'),
      rotation: gl.getAttribLocation(this.program!, 'a_rotation'),
    };

    this.uniformLocations = {
      resolution: gl.getUniformLocation(this.program!, 'u_resolution'),
      bloomIntensity: gl.getUniformLocation(this.program!, 'u_bloom_intensity'),
      themeMode: gl.getUniformLocation(this.program!, 'u_theme_mode'),
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
      const modeIdx = mode === 'light' ? 1 : mode === 'high-contrast' ? 2 : 0;
      if (this.uniformLocations.themeMode) {
        this.gl.uniform1i(this.uniformLocations.themeMode, modeIdx);
      }
    }
  }

  public getGridDimensions(): { cols: number; rows: number } {
    return { cols: this.cols, rows: this.rows };
  }

  public getThemeMode(): VFXThemeMode {
    return this.themeMode;
  }


  public resize(width: number, height: number): void {
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    if (this.gl) {
      this.gl.viewport(0, 0, width, height);
      if (this.program && this.uniformLocations.resolution) {
        this.gl.useProgram(this.program);
        this.gl.uniform2f(this.uniformLocations.resolution, width, height);
      }
    }
  }

  public triggerSpellVFX(params: SpellVFXParams): void {
    const archetype: SpellArchetype = params.spellArchetype ?? 'evocation';
    const targetPx = this.gridToPixel(params.toX, params.toY);

    const hasOrigin =
      params.fromX !== undefined &&
      params.fromY !== undefined &&
      (params.fromX !== params.toX || params.fromY !== params.toY);

    if (hasOrigin && archetype !== 'abjuration') {
      const startPx = this.gridToPixel(params.fromX!, params.fromY!);
      const dist = Math.hypot(targetPx.x - startPx.x, targetPx.y - startPx.y);
      const durationMs = Math.min(320, Math.max(160, dist * 0.9));

      const projectile: ActiveProjectile = {
        id: `proj-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
        spellName: params.spellName,
        spellArchetype: archetype,
        currentX: startPx.x,
        currentY: startPx.y,
        targetX: targetPx.x,
        targetY: targetPx.y,
        toGridX: params.toX,
        toGridY: params.toY,
        radiusPx: ((params.radiusFt ?? 20) / 5) * this.cellSizePx,
        color: getArchetypeColor(archetype, params.damageType),
        progress: 0,
        durationMs,
        elapsedMs: 0,
        startX: startPx.x,
        startY: startPx.y,
        onImpact: () => {
          this.explodeArchetype(archetype, targetPx.x, targetPx.y, params);
          if (params.onImpact) params.onImpact();
        },
        onFinish: params.onFinish,
      };
      this.projectiles.push(projectile);
    } else {
      this.explodeArchetype(archetype, targetPx.x, targetPx.y, params);
      if (params.onImpact) params.onImpact();
      if (params.onFinish) {
        setTimeout(params.onFinish, archetype === 'abjuration' ? 650 : 500);
      }
    }
  }

  private explodeArchetype(
    archetype: SpellArchetype,
    cx: number,
    cy: number,
    params: SpellVFXParams
  ): void {
    const sp = params.spellName.toLowerCase();
    const dt = (params.damageType || '').toLowerCase();

    if (archetype === 'abjuration' || sp.includes('shield')) {
      this.particles.push(...createAbjurationShieldParticles(cx, cy));
      this.addDecal(params.toX, params.toY, 'abjuration_glyph', 2);
    } else if (archetype === 'conjuration' || sp.includes('portal') || sp.includes('mist')) {
      this.particles.push(...createConjurationPortalParticles(cx, cy));
      this.addDecal(params.toX, params.toY, 'portal_residue', 2);
    } else if (sp.includes('lightning') || dt.includes('lightning')) {
      this.particles.push(...createLightningArcParticles(cx, cy));
      this.addDecal(params.toX, params.toY, 'lightning_scorch', 2);
    } else if (sp.includes('frost') || sp.includes('cold') || dt.includes('cold')) {
      this.particles.push(...createFrostBloomParticles(cx, cy));
      this.addDecal(params.toX, params.toY, 'frost', 2);
    } else {
      this.particles.push(...createFirestormParticles(cx, cy));
      this.addDecal(params.toX, params.toY, 'scorched_earth', 2);
    }
  }

  public spawnFirestorm(cx: number, cy: number, count = 75): void {
    this.particles.push(...createFirestormParticles(cx, cy, count));
  }

  public spawnLightningArc(cx: number, cy: number): void {
    this.particles.push(...createLightningArcParticles(cx, cy));
  }

  public spawnAbjurationShield(cx: number, cy: number): void {
    this.particles.push(...createAbjurationShieldParticles(cx, cy));
  }

  public spawnConjurationPortal(cx: number, cy: number): void {
    this.particles.push(...createConjurationPortalParticles(cx, cy));
  }

  public spawnFrostBloom(cx: number, cy: number): void {
    this.particles.push(...createFrostBloomParticles(cx, cy));
  }

  private addDecal(x: number, y: number, decalType: DecalType, durationRounds = 2): void {
    this.decals.push({
      id: `decal-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      x,
      y,
      decalType,
      durationRounds,
      roundsRemaining: durationRounds,
      opacity: 0.85,
      createdAt: Date.now(),
    });
  }

  public decayDecals(rounds = 1): EphemeralDecal[] {
    for (const d of this.decals) {
      d.roundsRemaining -= rounds;
      d.opacity = Math.max(0.15, (d.roundsRemaining / d.durationRounds) * 0.85);
    }
    this.decals = this.decals.filter((d) => d.roundsRemaining > 0);
    return this.decals;
  }

  public getDecals(): EphemeralDecal[] {
    return this.decals;
  }

  public getActiveParticlesCount(): number {
    return this.particles.length;
  }

  public getActiveProjectilesCount(): number {
    return this.projectiles.length;
  }

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
    this.projectiles = [];
    this.decals = [];
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

    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      const p = this.projectiles[i];
      p.elapsedMs += deltaMs;
      p.progress = Math.min(1.0, p.elapsedMs / p.durationMs);

      p.currentX = p.startX + (p.targetX - p.startX) * p.progress;
      p.currentY = p.startY + (p.targetY - p.startY) * p.progress;

      this.particles.push({
        x: p.currentX + (Math.random() - 0.5) * 4,
        y: p.currentY + (Math.random() - 0.5) * 4,
        vx: (Math.random() - 0.5) * 0.8,
        vy: (Math.random() - 0.5) * 0.8,
        size: 4 + Math.random() * 4,
        initialSize: 6,
        color: [p.color[0], p.color[1], p.color[2], 0.8],
        life: 1.0,
        maxLife: 0.25,
        age: 0,
        type: 0,
        rotation: 0,
        rotationSpeed: 0,
      });

      if (p.progress >= 1.0) {
        if (p.onImpact) p.onImpact();
        if (p.onFinish) p.onFinish();
        this.projectiles.splice(i, 1);
      }
    }

    for (let i = this.particles.length - 1; i >= 0; i--) {
      const pt = this.particles[i];
      pt.age += dtSec;
      pt.life = Math.max(0, 1.0 - pt.age / pt.maxLife);
      pt.x += pt.vx;
      pt.y += pt.vy;
      pt.rotation += pt.rotationSpeed;
      pt.size = pt.initialSize * pt.life;

      if (pt.life <= 0) {
        this.particles.splice(i, 1);
      }
    }

    if (this.particles.length > this.maxParticles) {
      this.particles.splice(0, this.particles.length - this.maxParticles);
    }
  }

  public render(): void {
    if (this.gl && this.program) {
      this.renderWebGL();
    } else if (this.ctx2d) {
      this.render2DFallback();
    }
  }

  private renderWebGL(): void {
    const gl = this.gl!;
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);

    if (this.particles.length === 0) return;

    gl.useProgram(this.program);

    const stride = 10;
    const vertexData = new Float32Array(this.particles.length * stride);

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      const offset = i * stride;
      vertexData[offset] = p.x;
      vertexData[offset + 1] = p.y;
      vertexData[offset + 2] = p.color[0];
      vertexData[offset + 3] = p.color[1];
      vertexData[offset + 4] = p.color[2];
      vertexData[offset + 5] = p.color[3];
      vertexData[offset + 6] = p.size;
      vertexData[offset + 7] = p.life;
      vertexData[offset + 8] = p.type;
      vertexData[offset + 9] = p.rotation;
    }

    gl.bindBuffer(gl.ARRAY_BUFFER, this.instancedBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertexData, gl.DYNAMIC_DRAW);

    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuffer);
    gl.enableVertexAttribArray(this.attribLocations.quadPos);
    gl.vertexAttribPointer(this.attribLocations.quadPos, 2, gl.FLOAT, false, 0, 0);

    const ext = gl.getExtension('ANGLE_instanced_arrays');
    if (ext) {
      gl.bindBuffer(gl.ARRAY_BUFFER, this.instancedBuffer);
      const byteStride = stride * 4;

      gl.enableVertexAttribArray(this.attribLocations.particlePos);
      gl.vertexAttribPointer(this.attribLocations.particlePos, 2, gl.FLOAT, false, byteStride, 0);
      ext.vertexAttribDivisorANGLE(this.attribLocations.particlePos, 1);

      gl.enableVertexAttribArray(this.attribLocations.color);
      gl.vertexAttribPointer(this.attribLocations.color, 4, gl.FLOAT, false, byteStride, 8);
      ext.vertexAttribDivisorANGLE(this.attribLocations.color, 1);

      gl.enableVertexAttribArray(this.attribLocations.size);
      gl.vertexAttribPointer(this.attribLocations.size, 1, gl.FLOAT, false, byteStride, 24);
      ext.vertexAttribDivisorANGLE(this.attribLocations.size, 1);

      gl.enableVertexAttribArray(this.attribLocations.life);
      gl.vertexAttribPointer(this.attribLocations.life, 1, gl.FLOAT, false, byteStride, 28);
      ext.vertexAttribDivisorANGLE(this.attribLocations.life, 1);

      gl.enableVertexAttribArray(this.attribLocations.type);
      gl.vertexAttribPointer(this.attribLocations.type, 1, gl.FLOAT, false, byteStride, 32);
      ext.vertexAttribDivisorANGLE(this.attribLocations.type, 1);

      gl.enableVertexAttribArray(this.attribLocations.rotation);
      gl.vertexAttribPointer(this.attribLocations.rotation, 1, gl.FLOAT, false, byteStride, 36);
      ext.vertexAttribDivisorANGLE(this.attribLocations.rotation, 1);

      ext.drawArraysInstancedANGLE(gl.TRIANGLES, 0, 6, this.particles.length);

      ext.vertexAttribDivisorANGLE(this.attribLocations.particlePos, 0);
      ext.vertexAttribDivisorANGLE(this.attribLocations.color, 0);
      ext.vertexAttribDivisorANGLE(this.attribLocations.size, 0);
      ext.vertexAttribDivisorANGLE(this.attribLocations.life, 0);
      ext.vertexAttribDivisorANGLE(this.attribLocations.type, 0);
      ext.vertexAttribDivisorANGLE(this.attribLocations.rotation, 0);
    }
  }

  private render2DFallback(): void {
    const ctx = this.ctx2d!;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

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

function programValid(gl: WebGLRenderingContext, program: WebGLProgram | null): boolean {
  return program !== null && gl.isProgram(program);
}
