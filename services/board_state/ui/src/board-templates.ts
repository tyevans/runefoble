/**
 * Board Templates Aggregator Facade
 *
 * Re-exports modular Lit HTML templates across kinematics, cell, and overlays
 * per ADR-0004, ADR-0012, and ADR-0013.
 */

export {
  getHealthBarColor,
  renderVectorOverlay,
  renderDistanceRuler,
  renderGhostBanner,
} from './templates/kinematics.template.ts';

export {
  type BoardCellProps,
  renderBoardCell,
} from './templates/cell.template.ts';

export {
  renderBoardHeader,
  renderStatusBar,
  renderRadialMenuOverlay,
  renderAoEOverlay,
  renderAoEBanner,
} from './templates/overlays.template.ts';
