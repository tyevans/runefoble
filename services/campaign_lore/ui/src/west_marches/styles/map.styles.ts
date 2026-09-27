import { css } from 'lit';

export const mapStyles = css`
  :host {
    display: block;
    position: relative;
    width: 100%;
    height: 100%;
  }

  .map-wrapper {
    flex: 1;
    width: 100%;
    height: 100%;
    position: relative;
    background: #f4f6f8;
    overflow: hidden;
    cursor: grab;
    user-select: none;
  }

  .map-wrapper:active {
    cursor: grabbing;
  }

  .map-svg, .hex-svg {
    width: 100%;
    height: 100%;
    position: absolute;
    top: 0;
    left: 0;
  }

  .frontier-grid {
    stroke: #e0e0e0;
    stroke-width: 1px;
  }

  .fog-boundary {
    fill: #1a202c;
    opacity: 0.12;
    stroke: #4a5568;
    stroke-dasharray: 4, 4;
  }

  .fog-text {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.1em;
    fill: #718096;
    text-transform: uppercase;
  }

  .map-controls {
    position: absolute;
    bottom: 16px;
    left: 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    z-index: 10;
  }

  .map-btn {
    width: 32px;
    height: 32px;
    font-size: 1.1rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #ffffff;
    border: 2px solid #121212;
    box-shadow: 2px 2px 0px #121212;
    cursor: pointer;
  }

  .filter-panel {
    position: absolute;
    top: 14px;
    left: 14px;
    background: #ffffff;
    border: 2px solid #121212;
    box-shadow: 3px 3px 0px #121212;
    padding: 10px;
    z-index: 10;
    display: flex;
    gap: 8px;
    align-items: center;
    font-size: 0.78rem;
  }

  .filter-select {
    padding: 4px 8px;
    font-size: 0.75rem;
    font-weight: 700;
    border: 1px solid #121212;
    background: #fafafa;
  }
`;
