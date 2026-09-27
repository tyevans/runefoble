import { css } from 'lit';
import { ghostStyles } from './ghost_preview.styles.ts';
import { boardTokenStyles } from './runefoble-board-tokens.styles.ts';

const baseBoardStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary);
    background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    padding: 16px;
    box-shadow: var(--rf-shadow);
    box-sizing: border-box;
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
    user-select: none;
    -webkit-user-select: none;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
    flex-wrap: wrap;
    gap: 12px;
  }

  .title {
    font-size: 1.25rem;
    font-weight: 800;
    color: var(--rf-text-primary);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .controls {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .watcher-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--rf-bg-canvas);
    color: var(--rf-text-primary);
    padding: 4px 10px;
    border-radius: var(--rf-border-radius, 0px);
    font-size: 0.75rem;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm);
    font-weight: 700;
  }

  .fog-toggle, .mode-3d-toggle {
    background: var(--rf-bg-surface);
    color: var(--rf-text-muted);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    padding: 4px 8px;
    font-size: 0.75rem;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    box-shadow: var(--rf-shadow-sm);
    transition: all 0.2s;
  }

  .fog-toggle.active {
    background: var(--rf-accent-tertiary);
    color: var(--rf-color-dark);
  }

  .mode-3d-toggle.active {
    background: var(--rf-accent-secondary);
    color: var(--rf-color-light);
  }

  .grid-wrapper {
    position: relative;
    width: fit-content;
    margin: 0 auto;
  }

  .vfx-particle-canvas, .tabletop-3d-canvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 10;
  }

  .tabletop-3d-canvas {
    z-index: 12;
    display: none;
  }

  .tabletop-3d-canvas.active {
    display: block;
  }


  .grid {
    display: grid;
    gap: 2px;
    background: var(--rf-border-color);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    overflow: hidden;
    position: relative;
    box-shadow: var(--rf-shadow-sm);
    touch-action: none;
  }

  .cell {
    width: 54px;
    height: 54px;
    background: var(--rf-bg-surface);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    cursor: pointer;
    transition: background 0.15s ease-in-out, filter 0.2s ease-in-out;
    box-sizing: border-box;
  }

  .cell:hover:not(.fog) {
    background: var(--rf-bg-canvas);
  }

  .cell.fog {
    background: var(--rf-color-dark);
    filter: brightness(0.6);
    cursor: not-allowed;
  }

  .cell.fog::after {
    content: '';
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
      45deg,
      rgba(0, 0, 0, 0.4),
      rgba(0, 0, 0, 0.4) 4px,
      rgba(0, 0, 0, 0.6) 4px,
      rgba(0, 0, 0, 0.6) 8px
    );
    pointer-events: none;
  }

  .status-bar {
    margin-top: 12px;
    font-size: 0.85rem;
    color: var(--rf-text-muted);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }

  .legend {
    display: flex;
    gap: 12px;
    font-size: 0.75rem;
    color: var(--rf-text-muted);
    flex-wrap: wrap;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 600;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: 1px solid var(--rf-border-color);
  }
`;

export const boardStyles = [baseBoardStyles, boardTokenStyles, ghostStyles];
