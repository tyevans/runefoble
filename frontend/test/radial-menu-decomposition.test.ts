/**
 * Unit & Integration tests for Board State Radial Menu Decomposition.
 * TASK-0201: Board State Radial Menu Glyphs and Styles Modular Decomposition
 * ADR-0004, ADR-0012, ADR-0013
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

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

describe('Radial Menu: Actions', () => {
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
