/**
 * Unit & Integration tests for Board Templates Rendering and Subviews Modular Decomposition.
 * TASK-0192: Board Templates Rendering and Subviews Modular Decomposition
 * ADR-0004, ADR-0012, ADR-0013
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { nothing } from 'lit';

// Test imports from aggregator facade
import {
  getHealthBarColor,
  renderVectorOverlay,
  renderDistanceRuler,
  renderGhostBanner,
  renderBoardCell,
  renderBoardHeader,
  renderStatusBar,
  renderRadialMenuOverlay,
  renderAoEOverlay,
  renderAoEBanner,
} from '../../services/board_state/ui/src/board-templates.ts';

// Test direct imports from modular sub-templates
import {
  getHealthBarColor as getHealthBarColorDirect,
  renderVectorOverlay as renderVectorOverlayDirect,
  renderDistanceRuler as renderDistanceRulerDirect,
  renderGhostBanner as renderGhostBannerDirect,
} from '../../services/board_state/ui/src/templates/kinematics.template.ts';

import {
  renderBoardCell as renderBoardCellDirect,
  type BoardCellProps,
} from '../../services/board_state/ui/src/templates/cell.template.ts';

import {
  renderBoardHeader as renderBoardHeaderDirect,
  renderStatusBar as renderStatusBarDirect,
  renderRadialMenuOverlay as renderRadialMenuOverlayDirect,
  renderAoEOverlay as renderAoEOverlayDirect,
  renderAoEBanner as renderAoEBannerDirect,
} from '../../services/board_state/ui/src/templates/overlays.template.ts';

describe('Board Templates: Kinematics Submodule', () => {
  it('re-exports match direct sub-template functions', () => {
    assert.equal(getHealthBarColor, getHealthBarColorDirect);
    assert.equal(renderVectorOverlay, renderVectorOverlayDirect);
    assert.equal(renderDistanceRuler, renderDistanceRulerDirect);
    assert.equal(renderGhostBanner, renderGhostBannerDirect);
  });

  it('calculates health bar color according to health ratio', () => {
    assert.equal(getHealthBarColor(10, 10), 'var(--rf-accent-secondary)');
    assert.equal(getHealthBarColor(6, 10), 'var(--rf-accent-secondary)');
    assert.equal(getHealthBarColor(5, 10), 'var(--rf-accent-tertiary)');
    assert.equal(getHealthBarColor(3, 10), 'var(--rf-accent-tertiary)');
    assert.equal(getHealthBarColor(2, 10), 'var(--rf-accent-primary)');
    assert.equal(getHealthBarColor(0, 10), 'var(--rf-accent-primary)');
    // Clamping checks
    assert.equal(getHealthBarColor(-5, 10), 'var(--rf-accent-primary)');
    assert.equal(getHealthBarColor(15, 10), 'var(--rf-accent-secondary)');
  });

  it('renders vector overlay or nothing if no vector', () => {
    assert.equal(renderVectorOverlay(null), nothing);

    const vectorResult = renderVectorOverlay({ x1: 50, y1: 50, x2: 150, y2: 150 });
    assert.notEqual(vectorResult, nothing);
    assert.ok(typeof vectorResult === 'object');
  });

  it('renders distance ruler or nothing if not dragging / distance <= 0', () => {
    assert.equal(renderDistanceRuler(null), nothing);
    assert.equal(
      renderDistanceRuler({
        isDragging: false,
        originX: 0,
        originY: 0,
        currentX: 0,
        currentY: 0,
        totalDistanceFt: 15,
        waypoints: [],
        difficultCells: [],
        hazardCells: [],
      }),
      nothing
    );
    assert.equal(
      renderDistanceRuler({
        isDragging: true,
        originX: 0,
        originY: 0,
        currentX: 0,
        currentY: 0,
        totalDistanceFt: 0,
        waypoints: [],
        difficultCells: [],
        hazardCells: [],
      }),
      nothing
    );

    const rulerResult = renderDistanceRuler({
      isDragging: true,
      originX: 0,
      originY: 0,
      currentX: 1,
      currentY: 1,
      totalDistanceFt: 15,
      waypoints: [{ x: 1, y: 1 }],
      difficultCells: [{ x: 1, y: 1, terrainType: 'difficult' }],
      hazardCells: [],
    });
    assert.notEqual(rulerResult, nothing);
  });

  it('renders ghost banner or nothing if no ghost preview', () => {
    let confirmed = false;
    let cancelled = false;
    assert.equal(renderGhostBanner(null, () => { confirmed = true; }, () => { cancelled = true; }), nothing);

    const bannerResult = renderGhostBanner(
      {
        tokenName: 'Aragorn',
        tokenId: 'token-1',
        fromX: 0,
        fromY: 0,
        toX: 2,
        toY: 3,
        totalDistanceFt: 25,
        remainingSeconds: 12,
        hazardTriggered: 'Spike Pit',
        damageDice: '2d6',
      },
      () => { confirmed = true; },
      () => { cancelled = true; }
    );
    assert.notEqual(bannerResult, nothing);
  });
});

describe('Board Templates: Cell Submodule', () => {
  it('re-exports match direct sub-template functions', () => {
    assert.equal(renderBoardCell, renderBoardCellDirect);
  });

  it('renders tactical grid cell with token and health bar', () => {
    const props: BoardCellProps = {
      x: 2,
      y: 3,
      isRevealed: true,
      isWaypoint: false,
      isActiveTurn: true,
      isGhostCell: false,
      selectedTokenId: 'token-1',
      token: {
        id: 'token-1',
        name: 'Gimli',
        x: 2,
        y: 3,
        color: '#e63946',
        hp: 25,
        maxHp: 30,
      },
      onCellClick: () => {},
      onTokenPointerDown: () => {},
      onGhostConfirm: () => {},
    };

    const cellResult = renderBoardCell(props);
    assert.ok(cellResult);
    assert.ok(typeof cellResult === 'object');
  });

  it('renders tactical grid cell with ghost token preview', () => {
    const props: BoardCellProps = {
      x: 4,
      y: 4,
      isRevealed: true,
      isWaypoint: true,
      isActiveTurn: false,
      isGhostCell: true,
      ghostName: 'Legolas',
      selectedTokenId: null,
      onCellClick: () => {},
      onTokenPointerDown: () => {},
      onGhostConfirm: () => {},
    };

    const cellResult = renderBoardCell(props);
    assert.ok(cellResult);
    assert.ok(typeof cellResult === 'object');
  });
});

describe('Board Templates: Overlays Submodule', () => {
  it('re-exports match direct sub-template functions', () => {
    assert.equal(renderBoardHeader, renderBoardHeaderDirect);
    assert.equal(renderStatusBar, renderStatusBarDirect);
    assert.equal(renderRadialMenuOverlay, renderRadialMenuOverlayDirect);
    assert.equal(renderAoEOverlay, renderAoEOverlayDirect);
    assert.equal(renderAoEBanner, renderAoEBannerDirect);
  });

  it('renders board header with 3D toggle and watcher status', () => {
    let fogToggled = false;
    let toggled3D = false;
    const headerResult = renderBoardHeader(
      true,
      () => { fogToggled = true; },
      'Listening...',
      false,
      () => { toggled3D = true; }
    );
    assert.ok(headerResult);
  });

  it('renders status bar with token info and grid dimensions', () => {
    const statusResult = renderStatusBar('Gandalf', 12, 12);
    assert.ok(statusResult);
  });

  it('renders radial menu overlay or nothing when token is null', () => {
    assert.equal(renderRadialMenuOverlay(null, () => {}, () => {}), nothing);

    const radialResult = renderRadialMenuOverlay(
      { id: 'token-1', name: 'Frodo', x: 1, y: 1 },
      () => {},
      () => {}
    );
    assert.notEqual(radialResult, nothing);
  });

  it('renders AoE overlay or nothing when AoE config is null', () => {
    assert.equal(renderAoEOverlay(null, [], 8, 8, () => {}), nothing);

    const aoeResult = renderAoEOverlay(
      {
        shape: 'sphere',
        originX: 2,
        originY: 2,
        directionDeg: 0,
        radiusFt: 20,
        spellName: 'Fireball',
      },
      [],
      8,
      8,
      () => {}
    );
    assert.notEqual(aoeResult, nothing);
  });

  it('renders AoE banner or nothing when AoE config is null', () => {
    assert.equal(renderAoEBanner(null, 0, () => {}, () => {}), nothing);

    const bannerResult = renderAoEBanner(
      {
        shape: 'cone',
        originX: 1,
        originY: 1,
        directionDeg: 45,
        lengthFt: 30,
        spellName: 'Cone of Cold',
      },
      3,
      () => {},
      () => {}
    );
    assert.notEqual(bannerResult, nothing);
  });
});
