import { css } from 'lit';

export const duplexMeterStyles = css`
  .visualizer-card {
    background: var(--rf-bg-inset, #18181b);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #111111);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgba(0, 0, 0, 0.9));
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    box-sizing: border-box;
  }
  .canvas-wrapper {
    position: relative;
    width: 100%;
    height: 52px;
    background: var(--rf-bg-canvas, #09090b);
    border: 1px solid var(--rf-border-subtle, #27272a);
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .duplex-canvas {
    width: 100%;
    height: 100%;
    display: block;
  }
  .barge-in-overlay {
    position: absolute;
    top: 4px;
    right: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 8px;
    background: var(--rf-accent-primary, #ef4444);
    color: var(--rf-text-inverse, #ffffff);
    font-size: 0.7rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1px solid var(--rf-border-color, #000000);
    animation: barge-pulse 0.8s infinite alternate;
  }
  @keyframes barge-pulse {
    0% { transform: scale(1); opacity: 0.9; }
    100% { transform: scale(1.05); opacity: 1; box-shadow: 0 0 8px var(--rf-accent-primary, #ef4444); }
  }
  .crossfade-overlay {
    position: absolute;
    bottom: 4px;
    left: 6px;
    padding: 2px 6px;
    background: var(--rf-accent-tertiary, #eab308);
    color: var(--rf-text-primary, #111111);
    font-size: 0.68rem;
    font-weight: 700;
    border: 1px solid var(--rf-border-color, #000000);
  }
  .meters-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 8px;
  }
  .meter-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .meter-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.68rem;
    font-weight: 700;
    color: var(--rf-text-muted, #71717a);
    text-transform: uppercase;
  }
  .meter-track {
    height: 8px;
    background: var(--rf-bg-canvas, #27272a);
    border: 1px solid var(--rf-border-color, #111111);
    overflow: hidden;
    position: relative;
  }
  .meter-fill {
    height: 100%;
    transition: width 0.08s ease;
    background: var(--rf-accent-secondary, #22c55e);
  }
  .meter-fill.warning {
    background: var(--rf-accent-tertiary, #eab308);
  }
  .meter-fill.alert {
    background: var(--rf-accent-primary, #ef4444);
  }
`;
