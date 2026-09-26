---
id: 0017
title: Bauhaus Geometric Dice Physics & Roll Arithmetic Web Component
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0004, TASK-0010, TASK-0012]
governing_adrs: [ADR-0004, ADR-0008, ADR-0012]
target_release: 0.1.0
---

# TASK-0017 — Bauhaus Geometric Dice Physics & Roll Arithmetic Web Component

## Status
Complete

## Summary
Implemented a high-impact, tactile Bauhaus geometric dice rolling Web Component `<runefoble-dice-roller>` and dice arithmetic evaluation engine (PRD-0001, ADR-0012). The component provides tactile rolling animations for polyhedral dice (D4, D6, D8, D10, D12, D20, D100) rendered with bold Bauhaus modernist geometry (pure squares, triangles, circles, and primary color blocks), full dice notation support (`2d20kh1+3`, `8d6+4`, `4d6kh3`), critical success/fumble highlights, and automatic dispatch of `DiceRolled` domain events.

## Scope & Key Changes
1. **Domain Event (`libs/runefoble_events/src/runefoble_events/events.py`)**:
   - Defined and registered `DiceRolled` domain event under `runefoble.events.dice.rolled` with `session_id`, `roller_id`, `roller_name`, `formula`, `total`, `rolls`, `is_crit`, and `is_fumble`.
   - Backward compatibility aliases and CloudEvents 1.0 serialization compliance.
   - Exported across `events.py` and `runefoble_events.__all__`.
2. **Dice Arithmetic Engine (`libs/runefoble_platform/src/runefoble_platform/dice.py`)**:
   - Implemented `parse_and_roll(formula: str) -> dict` and `evaluate_dice(count, sides, modifier, keep_highest, keep_lowest) -> dict`.
   - Evaluates standard TTRPG expressions (`1d20+5`, `2d20kh1+3` advantage, `2d20kl1+3` disadvantage, `8d6+4`, `4d6kh3`).
   - Flags critical hits (natural 20 on d20) and fumbles (natural 1 on d20).
   - Exported in `runefoble_platform.__all__`. Kept strictly under 250 lines (152 lines).
3. **Frontend TypeScript Parser (`frontend/src/utils/dice.ts`)**:
   - Zero-latency client-side arithmetic mirror parser supporting all formulas and keep rules.
4. **Bauhaus Web Component (`frontend/src/components/runefoble-dice-roller.ts`)**:
   - `<runefoble-dice-roller>` custom Lit element consuming Bauhaus design tokens (`var(--rf-bg-surface)`, `var(--rf-border-color)`, `var(--rf-shadow)`, `var(--rf-color-red)`, `var(--rf-color-blue)`, `var(--rf-color-yellow)`).
   - Geometric polyhedral dice selector chips (D4, D6, D8, D10, D12, D20, D100).
   - Quick stance toggles: "Advantage (+d20 kh1)", "Normal", "Disadvantage (+d20 kl1)".
   - Animated rolling state with tactile drop-shadow displacement (`transform: translate(2px, 2px)`).
   - Big bold result display:
     - Natural 20 / Critical Hit displayed with vibrant yellow banner and confetti-like geometric particles.
     - Natural 1 / Fumble displayed with stark red warning border.
   - Dispatches `dice-rolled` CustomEvent with full detail payload.
   - Kept strictly under 400 lines (288 lines).
5. **Storybook Stories (`frontend/src/stories/dice-roller.stories.ts`)**:
   - `StandardD20Roll`, `AdvantageAttack`, `Fireball8d6`, `CriticalHit`, `CriticalFumble`.
6. **Application Integration**:
   - Exported in `frontend/src/index.ts` and integrated in `frontend/src/runefoble-app.ts`.
7. **Testing (`tests/test_dice_roller.py`)**:
   - Property-based tests using `hypothesis` verifying roll bounds ($count \times 1 + modifier \le total \le count \times sides + modifier$) and keep-highest invariants.
   - Unit tests for advantage `2d20kh1`, disadvantage `2d20kl1`, stat generation `4d6kh3`, Fireball `8d6+4`, crits, and fumbles.
   - CloudEvents 1.0 schema compliance and event registry tests.
