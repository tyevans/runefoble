import { css } from 'lit';
import { ghostStyles } from './ghost_preview.styles.ts';

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

  .fog-toggle {
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

  .grid-wrapper {
    position: relative;
    width: fit-content;
    margin: 0 auto;
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

  /* Terrain types */
  .cell.difficult-terrain {
    background: repeating-linear-gradient(
      45deg,
      rgba(255, 183, 3, 0.16),
      rgba(255, 183, 3, 0.16) 6px,
      rgba(255, 255, 255, 0.6) 6px,
      rgba(255, 255, 255, 0.6) 12px
    );
  }

  .cell.hazard-cell {
    background: rgba(230, 57, 70, 0.18);
    border: 1.5px dashed var(--rf-accent-primary);
  }

  .cell.waypoint-path {
    background: rgba(69, 123, 157, 0.22);
  }

  .cell.waypoint-path.difficult-terrain {
    background: rgba(255, 183, 3, 0.35);
  }

  .cell.waypoint-path.hazard-cell {
    background: rgba(230, 57, 70, 0.35);
    animation: hazard-flash 1s infinite alternate;
  }

  @keyframes hazard-flash {
    0% {
      background: rgba(230, 57, 70, 0.25);
    }
    100% {
      background: rgba(230, 57, 70, 0.55);
    }
  }

  .terrain-badge {
    position: absolute;
    bottom: 2px;
    right: 2px;
    font-size: 0.55rem;
    font-weight: 800;
    pointer-events: none;
    padding: 1px 3px;
    border-radius: 2px;
    line-height: 1;
  }

  .terrain-badge.difficult {
    background: var(--rf-accent-tertiary);
    color: var(--rf-color-dark);
  }

  .terrain-badge.hazard {
    background: var(--rf-accent-primary);
    color: var(--rf-text-inverse);
  }

  .coord-label {
    position: absolute;
    top: 2px;
    left: 2px;
    font-size: 0.6rem;
    color: var(--rf-text-muted);
    pointer-events: none;
    user-select: none;
    font-weight: 700;
  }

  .token-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    z-index: 2;
  }

  .token {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 0.75rem;
    color: var(--rf-text-inverse);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm);
    user-select: none;
    transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1);
    position: relative;
    cursor: grab;
    touch-action: none;
  }

  .token:active {
    cursor: grabbing;
  }

  .token.dragging {
    cursor: grabbing;
    transform: scale(1.18);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.35);
    z-index: 100;
  }

  .token:hover:not(.dragging) {
    transform: scale(1.12);
    box-shadow: var(--rf-shadow);
  }

  .token.ai {
    outline: 2px dashed var(--rf-accent-tertiary);
    outline-offset: 1px;
  }

  .token.hostile {
    outline: 2px solid var(--rf-accent-primary);
    outline-offset: 1px;
  }

  .token.active-turn {
    animation: gold-pulse 1.6s infinite ease-in-out;
    outline: 3px solid var(--rf-accent-tertiary);
  }

  @keyframes gold-pulse {
    0% {
      box-shadow: 0 0 0 0 rgba(255, 183, 3, 0.8), var(--rf-shadow-sm);
    }
    70% {
      box-shadow: 0 0 0 8px rgba(255, 183, 3, 0), var(--rf-shadow-sm);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(255, 183, 3, 0), var(--rf-shadow-sm);
    }
  }

  .health-bar-container {
    width: 36px;
    height: 6px;
    background: var(--rf-bg-canvas);
    border: 1px solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    margin-top: 2px;
    overflow: hidden;
  }

  .health-bar-fill {
    height: 100%;
    transition: width 0.3s ease-in-out, background 0.3s ease-in-out;
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

export const boardStyles = [baseBoardStyles, ghostStyles];
