import { css } from 'lit';

export const diceTrayStyles = css`
  :host {
    display: block;
    position: relative;
    background: var(--rf-bg-surface, #090d16);
    border: var(--rf-border-width, 3px) solid var(--rf-border-color, #334155);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.6);
    box-sizing: border-box;
  }
  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
  .tray-hud {
    position: absolute;
    bottom: 8px;
    left: 10px;
    right: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    pointer-events: none;
  }
  .result-badge {
    background: var(--rf-bg-canvas, #1e293b);
    color: var(--rf-text-primary, #f8fafc);
    padding: 4px 10px;
    font-weight: 800;
    font-size: 0.85rem;
    border: 1px solid var(--rf-border-color, #475569);
    border-radius: 4px;
  }
`;
