/**
 * Spell Archetype particle generators and element color palettes.
 * Provides Evocation (firestorm, lightning, frost), Abjuration (runic ward), and Conjuration (portal).
 */

import type { DecalType, Particle, SpellArchetype } from './particle_types.ts';

export function getArchetypeColor(
  archetype: SpellArchetype,
  damageType?: string
): [number, number, number, number] {
  const dt = (damageType || '').toLowerCase();
  if (archetype === 'abjuration') return [0.2, 0.7, 1.0, 0.9];
  if (archetype === 'conjuration') return [0.7, 0.3, 0.95, 0.9];
  if (dt.includes('lightning')) return [0.35, 0.85, 1.0, 0.95];
  if (dt.includes('cold')) return [0.8, 0.95, 1.0, 0.9];
  return [1.0, 0.45, 0.1, 0.95]; // Evocation Fire
}

export function createFirestormParticles(cx: number, cy: number, count = 75): Particle[] {
  const result: Particle[] = [];
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 1.5 + Math.random() * 4.5;
    const maxLife = 0.4 + Math.random() * 0.5;
    const isCore = Math.random() > 0.4;

    result.push({
      x: cx + (Math.random() - 0.5) * 12,
      y: cy + (Math.random() - 0.5) * 12,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      size: isCore ? 8 + Math.random() * 8 : 4 + Math.random() * 6,
      initialSize: isCore ? 14 : 7,
      color: isCore
        ? [1.0, 0.4 + Math.random() * 0.4, 0.1, 0.95]
        : [0.9, 0.15, 0.05, 0.8],
      life: 1.0,
      maxLife,
      age: 0,
      type: 0, // radial bloom
      rotation: Math.random() * Math.PI,
      rotationSpeed: (Math.random() - 0.5) * 0.1,
    });
  }
  return result;
}

export function createLightningArcParticles(cx: number, cy: number, branches = 6): Particle[] {
  const result: Particle[] = [];
  for (let b = 0; b < branches; b++) {
    let curX = cx;
    let curY = cy;
    const baseAngle = (b / branches) * Math.PI * 2 + (Math.random() - 0.5) * 0.4;
    for (let s = 0; s < 7; s++) {
      const segLen = 8 + Math.random() * 12;
      const angle = baseAngle + (Math.random() - 0.5) * 0.8;
      const nextX = curX + Math.cos(angle) * segLen;
      const nextY = curY + Math.sin(angle) * segLen;

      result.push({
        x: (curX + nextX) / 2,
        y: (curY + nextY) / 2,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: 6 + Math.random() * 6,
        initialSize: 8,
        color: [0.4, 0.8, 1.0, 0.95],
        life: 1.0,
        maxLife: 0.25 + Math.random() * 0.25,
        age: 0,
        type: 1, // lightning beam
        rotation: angle,
        rotationSpeed: 0,
      });
      curX = nextX;
      curY = nextY;
    }
  }
  return result;
}

export function createAbjurationShieldParticles(cx: number, cy: number): Particle[] {
  const result: Particle[] = [];
  for (let i = 0; i < 3; i++) {
    result.push({
      x: cx,
      y: cy,
      vx: 0,
      vy: 0,
      size: 32 + i * 8,
      initialSize: 32 + i * 8,
      color: [0.2, 0.7, 1.0, 0.85],
      life: 1.0,
      maxLife: 0.7 + i * 0.1,
      age: 0,
      type: 2, // hex rune
      rotation: (i * Math.PI) / 6,
      rotationSpeed: 0.04 * (i % 2 === 0 ? 1 : -1),
    });
  }
  return result;
}

export function createConjurationPortalParticles(cx: number, cy: number, count = 50): Particle[] {
  const result: Particle[] = [];
  for (let i = 0; i < count; i++) {
    const radius = 6 + Math.random() * 32;
    const angle = Math.random() * Math.PI * 2;
    result.push({
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
      vx: -Math.sin(angle) * (1.2 + Math.random()),
      vy: Math.cos(angle) * (1.2 + Math.random()),
      size: 8 + Math.random() * 10,
      initialSize: 14,
      color: [0.65, 0.2, 0.9, 0.85],
      life: 1.0,
      maxLife: 0.55 + Math.random() * 0.35,
      age: 0,
      type: 3, // spiral vortex
      rotation: angle,
      rotationSpeed: 0.08,
    });
  }
  return result;
}

export function createFrostBloomParticles(cx: number, cy: number, count = 60): Particle[] {
  const result: Particle[] = [];
  for (let i = 0; i < count; i++) {
    const angle = (i / count) * Math.PI * 2;
    const speed = 1.0 + Math.random() * 3.0;
    result.push({
      x: cx,
      y: cy,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      size: 6 + Math.random() * 6,
      initialSize: 8,
      color: [0.8, 0.95, 1.0, 0.9],
      life: 1.0,
      maxLife: 0.45 + Math.random() * 0.35,
      age: 0,
      type: 0,
      rotation: Math.random() * Math.PI,
      rotationSpeed: (Math.random() - 0.5) * 0.05,
    });
  }
  return result;
}

export function createArchetypeParticles(
  archetype: SpellArchetype,
  cx: number,
  cy: number,
  spellName = '',
  damageType = ''
): { particles: Particle[]; decalType: DecalType } {
  const sp = spellName.toLowerCase();
  const dt = damageType.toLowerCase();
  if (archetype === 'abjuration' || sp.includes('shield')) {
    return { particles: createAbjurationShieldParticles(cx, cy), decalType: 'abjuration_glyph' };
  }
  if (archetype === 'conjuration' || sp.includes('portal') || sp.includes('mist')) {
    return { particles: createConjurationPortalParticles(cx, cy), decalType: 'portal_residue' };
  }
  if (sp.includes('lightning') || dt.includes('lightning')) {
    return { particles: createLightningArcParticles(cx, cy), decalType: 'lightning_scorch' };
  }
  if (sp.includes('frost') || sp.includes('cold') || dt.includes('cold')) {
    return { particles: createFrostBloomParticles(cx, cy), decalType: 'frost' };
  }
  return { particles: createFirestormParticles(cx, cy), decalType: 'scorched_earth' };
}
