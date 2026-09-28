# How-To: Trigger Multi-Modal Kinetic Spell VFX & WebGL Particle Magic

This guide explains how to use the high-performance WebGL particle visual effects engine, archetype shaders, voice-to-VFX pipeline, and ephemeral grid decals on the Runefoble tactical board (`<runefoble-tactical-board>` / `<runefoble-board>`).

---

## 1. WebGL Particle Engine Architecture

The visual effects overlay runs an instanced GPU particle system at 60fps directly above the tactical grid canvas with zero layout shift, decomposed into single-responsibility modules:
- **Core Canvas Engine (`particle_canvas.ts`)**: Coordinates WebGL context, animation loop, buffer management, and viewport resizing (< 260 lines).
- **Projectile Physics (`particle_projectiles.ts`)**: Calculates ballistic arcs, parabolic trajectories, trail particle generation, and impact collision checks (`ProjectileManager`).
- **Combat Grid Decals (`particle_decals.ts`)**: Manages ephemeral ground scorch marks, rune wards, and round-by-round opacity decay curves (`DecalManager`).
- **Billboard Instancing**: GPU draws up to 800 active particles per frame using `drawArraysInstancedANGLE`.
- **Zero Layout Shift**: Canvas is absolutely positioned within the grid wrapper, matching the tactical grid dimensions dynamically via `ResizeObserver`.
- **Graceful Fallback**: If WebGL is unavailable or unaccelerated in headless/test environments, the engine seamlessly falls back to 2D canvas rendering with decal overlays.

---

## 2. Spell Archetypes & Shaders

The particle engine ships with distinct spell archetype shaders and element palettes:

| Archetype | Element / Effect | Particle Dynamics | Shading & Appearance |
|---|---|---|---|
| **Evocation** | Firestorm / Fireball | Fast radial burst, turbulent tumbling embers, lingering fire trail | Additive fiery orange/yellow glow, soft bloom falloff |
| **Evocation** | Chain Lightning Arc | Zigzagging segmented ionizing beams, branching sparks | Sharp electric blue/cyan high-frequency beams |
| **Evocation** | Frost Bloom | Symmetrical crystalline expansion, icy particulate | Bright translucent white/cyan cold sparkles |
| **Abjuration** | Arcane Ward / Shield | Rotating hexagonal runic barrier (6-fold symmetry) | Translucent azure barrier with protective edge rings |
| **Conjuration** | Dimensional Portal | Inward/outward spiral vortex with purple mist | Non-linear logarithmic spiral particles with soft core |

---

## 3. Voice-to-VFX Pipeline (<150ms SLA)

Per US-0048, spoken spell incantations (e.g., *"I cast Fireball centered at coordinate D7"*) trigger visual effects in under 150ms:

1. **Speech-to-Intent**: The Watcher parses speech into `action_type: "cast_spell"` with extracted target coordinates.
2. **WebSocket Broadcast**: Server publishes `spell_vfx` payload to `/ws/boards/{session_id}`.
3. **Trajectory & Impact Bloom**:
   - For projectile spells (Fireball, Lightning), an active projectile streaks from the caster miniature to the target coordinates in ~250ms, producing a spark trail.
   - Upon impact, the target cell explodes into the archetype's particle bloom and plays the corresponding spatial audio stinger (e.g., `evocation_fireball_stinger`).
   - For reaction wards (Shield), the hexagonal shield barrier renders immediately around the caster's token.

---

## 4. Ephemeral Grid Decals & Natural Cleanup

To prevent board clutter while maintaining physical impact:
- Explosions spawn temporary terrain decals:
  - `scorched_earth` for fire spells.
  - `frost` for cold spells.
  - `lightning_scorch` for electricity.
  - `abjuration_glyph` for wards.
  - `portal_residue` for conjuration.
- **Round-based Decay**: Decals naturally fade over 2 combat rounds (`duration_rounds: 2`). Advancing combat rounds decays decal opacity and cleans up expired marks.

---

## 5. ADR-0012 Theme Bloom Calibration

The particle shader automatically calibrates its luminance and contrast across themes:
- **Dark Mode**: Additive emissive bloom (`gl.blendFunc(gl.SRC_ALPHA, gl.ONE)`) with bloom intensity `1.5`.
- **Light Mode**: Contrast-calibrated bloom with deepened core saturation (`gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)`) to ensure >4.5:1 contrast ratio against bright board backgrounds.
- **High-Contrast Mode**: Enhanced edge definition and boosted bloom intensity `1.3`.

```typescript
// Dynamically calibrate particle bloom across themes
boardElement.setThemeMode('light');
```

---

## 6. Programmatic Component Usage

```html
<runefoble-tactical-board
  .cols="${10}"
  .rows="${10}"
  .tokens="${activeTokens}"
  id="tacticalBoard"
></runefoble-tactical-board>

<script>
  const board = document.getElementById('tacticalBoard');

  // Trigger kinetic spell VFX directly
  board.triggerSpellVFX({
    spellName: 'Fireball',
    spellArchetype: 'evocation',
    fromX: 2,
    fromY: 3,
    toX: 6,
    toY: 5,
    radiusFt: 20,
    damageType: 'fire',
    onImpact: () => console.log('Fireball detonated!'),
  });
</script>
```

---

## 7. Modular Blackbox Test Suite Architecture

Under TASK-0191 (ADR-0003, ADR-0007, ADR-0010, ADR-0013, and Hard Invariant 6), the blackbox test suite is organized into focused submodules under `tests/test_blackbox_spell_vfx/`:

- **`conftest.py`**: Shared test harness, `MockSpiceDBClient`, `MockAsyncRedis`, FastAPI `TestClient`, and spell archetype payload fixtures (< 60 lines).
- **`test_spell_adjudication.py`**: Public REST spellcasting routes, Evocation/Abjuration/Conjuration archetypes, trajectory generation, and SLA latency verification (< 120 lines).
- **`test_decals_and_lifecycle.py`**: Ephemeral decal decay over rounds, fading opacity, animation completion callbacks, and WebGL particle canvas contracts (< 100 lines).
- **`test_speech_vfx_triggers.py`**: Real-time WebSocket speech-to-VFX triggers, sub-150ms broadcast SLA, and event sourcing domain events persistence (< 110 lines).

