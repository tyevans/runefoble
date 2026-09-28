/**
 * Unit & Integration tests for Board State Radial Menu Decomposition.
 * TASK-0201: Board State Radial Menu Glyphs and Styles Modular Decomposition
 * ADR-0004, ADR-0012, ADR-0013
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// Submodule imports via radial index facade
import {
  RADIAL_ACTIONS,
  radialMenuStyles,
  renderBauhausGlyph,
  polarToCartesian,
  describeArc,
  calculateWedgePosition,
  renderWedge,
} from '../../services/board_state/ui/src/radial/index.ts';

// Direct submodule imports
import { radialMenuStyles as stylesDirect } from '../../services/board_state/ui/src/radial/radial_menu.styles.ts';
import { renderBauhausGlyph as glyphDirect } from '../../services/board_state/ui/src/radial/radial_glyphs.ts';
import {
  RADIAL_ACTIONS as actionsDirect,
  polarToCartesian as polarDirect,
  describeArc as arcDirect,
  calculateWedgePosition as wedgePosDirect,
  renderWedge as renderWedgeDirect,
} from '../../services/board_state/ui/src/radial/radial_wedge.ts';

const REPO_ROOT = resolve(import.meta.dirname, '../../');

describe('Radial Menu Architecture: File Length Invariants (Hard Invariant 6)', () => {
  it('verifies radial_menu.ts is strictly < 110 lines (target < 100 lines)', () => {
    const filePath = resolve(REPO_ROOT, 'services/board_state/ui/src/radial_menu.ts');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(lines < 110, `radial_menu.ts has ${lines} lines, expected < 110`);
    assert.ok(lines < 100, `radial_menu.ts has ${lines} lines, expected target < 100`);
  });

  it('verifies radial_menu.styles.ts is strictly < 110 lines (target < 90 lines)', () => {
    const filePath = resolve(REPO_ROOT, 'services/board_state/ui/src/radial/radial_menu.styles.ts');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(lines < 110, `radial_menu.styles.ts has ${lines} lines, expected < 110`);
    assert.ok(lines < 90, `radial_menu.styles.ts has ${lines} lines, expected target < 90`);
  });

  it('verifies radial_glyphs.ts is strictly < 110 lines (target < 100 lines)', () => {
    const filePath = resolve(REPO_ROOT, 'services/board_state/ui/src/radial/radial_glyphs.ts');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(lines < 110, `radial_glyphs.ts has ${lines} lines, expected < 110`);
    assert.ok(lines < 100, `radial_glyphs.ts has ${lines} lines, expected target < 100`);
  });

  it('verifies radial_wedge.ts is strictly < 110 lines (target < 90 lines)', () => {
    const filePath = resolve(REPO_ROOT, 'services/board_state/ui/src/radial/radial_wedge.ts');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(lines < 110, `radial_wedge.ts has ${lines} lines, expected < 110`);
    assert.ok(lines < 90, `radial_wedge.ts has ${lines} lines, expected target < 90`);
  });
});

describe('Radial Menu: Submodule Re-exports and Direct Functions', () => {
  it('facade re-exports match direct submodule implementations', () => {
    assert.equal(radialMenuStyles, stylesDirect);
    assert.equal(renderBauhausGlyph, glyphDirect);
    assert.equal(RADIAL_ACTIONS, actionsDirect);
    assert.equal(polarToCartesian, polarDirect);
    assert.equal(describeArc, arcDirect);
    assert.equal(calculateWedgePosition, wedgePosDirect);
    assert.equal(renderWedge, renderWedgeDirect);
  });

  it('defines 5 standard tactical actions in RADIAL_ACTIONS', () => {
    assert.equal(RADIAL_ACTIONS.length, 5);
    const actionIds = RADIAL_ACTIONS.map((a) => a.id);
    assert.deepEqual(actionIds, ['attack', 'dash', 'disengage', 'dodge', 'cast']);
  });
});

describe('Radial Trigonometry & Polar Coordinate Calculations', () => {
  it('converts polar coordinates to cartesian coordinates correctly', () => {
    const right = polarToCartesian(0, 0, 100, 0);
    assert.equal(right.x, 100);
    assert.equal(right.y, 0);

    const down = polarToCartesian(0, 0, 100, Math.PI / 2);
    assert.equal(down.x, 0);
    assert.equal(down.y, 100);

    const left = polarToCartesian(0, 0, 100, Math.PI);
    assert.equal(left.x, -100);
    assert.equal(left.y, 0);
  });

  it('computes top-anchored circular layout positions', () => {
    const topPos = calculateWedgePosition(0, 5, 68);
    assert.equal(topPos.x, 0);
    assert.equal(topPos.y, -68);

    for (let i = 0; i < 5; i++) {
      const pos = calculateWedgePosition(i, 5, 68);
      const dist = Math.hypot(pos.x, pos.y);
      assert.ok(Math.abs(dist - 68) <= 1, `Expected dist ~68, got ${dist}`);
    }
  });

  it('generates valid SVG arc path commands', () => {
    const arcPath = describeArc(0, 0, 50, 0, Math.PI / 2);
    assert.ok(arcPath.startsWith('M '));
    assert.ok(arcPath.includes(' A 50 50 0'));
  });
});

describe('Bauhaus Geometric Glyphs', () => {
  it('renders SVG templates for all supported action icons', () => {
    const icons = ['attack', 'dash', 'disengage', 'dodge', 'cast'];
    for (const icon of icons) {
      const svgResult = renderBauhausGlyph(icon);
      assert.ok(svgResult, `renderBauhausGlyph(${icon}) returned nullish`);
      assert.ok(svgResult.strings.length > 0);
    }
  });

  it('renders fallback circle glyph for unknown icon', () => {
    const fallback = renderBauhausGlyph('unknown-ability');
    assert.ok(fallback);
    const joined = fallback.strings.join('');
    assert.ok(joined.includes('circle'));
  });
});

describe('Radial Wedge Rendering Template', () => {
  it('produces Lit HTML template with action label and position coordinates', () => {
    let clicked = false;
    const wedgeTemplate = renderWedge({
      action: RADIAL_ACTIONS[0],
      isActive: true,
      x: 15,
      y: -50,
      onMouseEnter: () => {},
      onMouseLeave: () => {},
      onPointerDown: () => {},
      onPointerUp: () => {},
      onClick: () => { clicked = true; },
    });

    assert.ok(wedgeTemplate);
    assert.ok(wedgeTemplate.values.includes('Attack'));
    assert.ok(wedgeTemplate.values.includes('active'));
    assert.ok(wedgeTemplate.values.includes(15));
    assert.ok(wedgeTemplate.values.includes(-50));
  });
});

describe('Web Component Controller Contract', () => {
  it('verifies radial_menu.ts exports RunefobleRadialMenu custom element and submodules', () => {
    const filePath = resolve(REPO_ROOT, 'services/board_state/ui/src/radial_menu.ts');
    const content = readFileSync(filePath, 'utf-8');
    assert.ok(content.includes("@customElement('runefoble-radial-menu')"));
    assert.ok(content.includes('export class RunefobleRadialMenu'));
    assert.ok(content.includes("export * from './radial/index.ts'"));
    assert.ok(content.includes("'runefoble-radial-menu': RunefobleRadialMenu"));
  });
});
