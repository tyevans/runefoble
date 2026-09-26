import { css } from 'lit';

export const combatHeatmapStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, 'Space Grotesk', system-ui, sans-serif);
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    padding: 16px;
    box-sizing: border-box;
  }

  .heatmap-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 10px;
    margin-bottom: 14px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .heatmap-title {
    font-size: 1.1rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .metric-filters {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .filter-btn {
    background: var(--rf-bg-surface, #ffffff);
    border: 1px solid var(--rf-border-color, #121212);
    color: var(--rf-text-primary, #121212);
    padding: 4px 10px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    cursor: pointer;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    font-family: inherit;
    transition: transform 0.1s ease;
  }

  .filter-btn:hover {
    transform: translate(-1px, -1px);
    background: var(--rf-bg-card, #f0f0f0);
  }

  .filter-btn.active {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
    box-shadow: none;
    transform: translate(1px, 1px);
  }

  .canvas-container {
    position: relative;
    width: 100%;
    overflow-x: auto;
    background: var(--rf-bg-inset, #1a1a1a);
    border: 1px solid var(--rf-border-color, #121212);
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 320px;
    padding: 12px;
    box-sizing: border-box;
  }

  canvas {
    display: block;
    image-rendering: pixelated;
    background: var(--rf-bg-surface, #ffffff);
    border: 2px solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    cursor: crosshair;
  }

  .legend-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 12px;
    padding: 8px 12px;
    background: var(--rf-bg-card, #f7f7f7);
    border: 1px solid var(--rf-border-color, #121212);
    font-size: 0.75rem;
    font-weight: 700;
    flex-wrap: wrap;
    gap: 8px;
  }

  .legend-scale {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .scale-gradient {
    width: 120px;
    height: 10px;
    border: 1px solid var(--rf-border-color, #121212);
    background: linear-gradient(to right, rgba(42, 157, 143, 0.4), #e9c46a, #f4a261, #e63946);
  }

  .legend-items {
    display: flex;
    gap: 12px;
  }

  .legend-badge {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .badge-icon {
    width: 10px;
    height: 10px;
    border: 1px solid var(--rf-border-color, #121212);
  }

  .inspector-card {
    margin-top: 12px;
    background: var(--rf-bg-card, #fafafa);
    border: 1px solid var(--rf-border-color, #121212);
    padding: 10px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.8rem;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    flex-wrap: wrap;
    gap: 8px;
  }

  .inspector-title {
    font-weight: 800;
    text-transform: uppercase;
  }

  .inspector-stats {
    display: flex;
    gap: 14px;
    font-weight: 600;
  }

  .stat-pill {
    padding: 2px 6px;
    background: var(--rf-bg-surface, #ffffff);
    border: 1px solid var(--rf-border-color, #121212);
  }
`;
