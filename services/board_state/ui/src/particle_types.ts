/**
 * Types and interfaces for tactical WebGL particle magic and kinetic spell VFX.
 */

export type SpellArchetype =
  | 'evocation'
  | 'abjuration'
  | 'conjuration'
  | 'transmutation'
  | 'necromancy'
  | 'enchantment'
  | 'illusion'
  | 'divination';

export type DecalType =
  | 'scorched_earth'
  | 'frost'
  | 'lightning_scorch'
  | 'abjuration_glyph'
  | 'portal_residue';

export interface EphemeralDecal {
  id: string;
  x: number; // grid col
  y: number; // grid row
  decalType: DecalType;
  durationRounds: number;
  roundsRemaining: number;
  opacity: number;
  createdAt: number;
}

export interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  initialSize: number;
  color: [number, number, number, number];
  life: number;
  maxLife: number;
  age: number;
  type: number; // 0=burst/radial, 1=lightning segment, 2=hex rune, 3=spiral vortex
  rotation: number;
  rotationSpeed: number;
}

export interface SpellVFXParams {
  spellName: string;
  spellArchetype?: SpellArchetype;
  fromX?: number; // grid column
  fromY?: number; // grid row
  toX: number; // grid column
  toY: number; // grid row
  radiusFt?: number;
  damageType?: string;
  themePalette?: string;
  onImpact?: () => void;
  onFinish?: () => void;
}

export interface ActiveProjectile {
  id: string;
  spellName: string;
  spellArchetype: SpellArchetype;
  currentX: number;
  currentY: number;
  targetX: number;
  targetY: number;
  toGridX: number;
  toGridY: number;
  radiusPx: number;
  color: [number, number, number, number];
  progress: number; // 0..1
  durationMs: number;
  elapsedMs: number;
  startX: number;
  startY: number;
  onImpact?: () => void;
  onFinish?: () => void;
}

export type VFXThemeMode = 'dark' | 'light' | 'system' | 'high-contrast';

export interface ParticleEngineOptions {
  cellSizePx?: number;
  cols?: number;
  rows?: number;
  maxParticles?: number;
  themeMode?: VFXThemeMode;
}

export function parseIncomingSpellVFX(data: any): SpellVFXParams | null {
  const action = data?.action || data?.type;
  if (action === 'spell_vfx' || action === 'SpellCast' || action === 'cast_spell') {
    const cast = data.spell_cast || data;
    return {
      spellName: cast.spell_name || 'Fireball',
      spellArchetype: cast.spell_archetype || 'evocation',
      fromX: cast.origin_x,
      fromY: cast.origin_y,
      toX: cast.target_x ?? cast.to_x ?? 0,
      toY: cast.target_y ?? cast.to_y ?? 0,
      radiusFt: cast.radius_ft ?? 20,
      damageType: cast.damage_type,
      themePalette: cast.theme_palette,
    };
  }
  return null;
}

