import { css } from 'lit';

export const boardTokenStyles = css`
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

  /* Targeting Halo for AoE target intersections */
  .token.target-halo {
    animation: target-halo-pulse 0.8s infinite alternate ease-in-out;
    outline: 3px solid var(--rf-accent-primary, #e63946);
    outline-offset: 3px;
  }

  @keyframes target-halo-pulse {
    0% {
      box-shadow: 0 0 6px 2px rgba(230, 57, 70, 0.6), var(--rf-shadow-sm);
      transform: scale(1.02);
    }
    100% {
      box-shadow: 0 0 16px 6px rgba(230, 57, 70, 0.95), var(--rf-shadow);
      transform: scale(1.10);
    }
  }

  .cell.aoe-affected-cell {
    background: rgba(230, 57, 70, 0.16);
  }

  .token-action-badge {
    position: absolute;
    top: -6px;
    right: -6px;
    font-size: 8px;
    font-weight: 800;
    text-transform: uppercase;
    background: var(--rf-accent-tertiary, #ffb703);
    color: #121212;
    border: 1px solid var(--rf-border-color, #121212);
    border-radius: 2px;
    padding: 0 3px;
    pointer-events: none;
    box-shadow: 1px 1px 0px var(--rf-shadow-color, #121212);
    z-index: 10;
  }
`;

