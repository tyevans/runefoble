import { css } from 'lit';

export const atlasStyles = css`
  :host {
    display: flex;
    flex-direction: column;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    color: var(--rf-text-primary, #121212);
    width: 960px;
    height: 640px;
    max-width: 100%;
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
  }

  .top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: #fafafa;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    z-index: 10;
  }

  .title-group {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .title {
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: -0.02em;
  }

  .layer-badge {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 2px 8px;
    border: 1px solid var(--rf-border-color, #121212);
    background: var(--rf-accent-tertiary, #ffb703);
    text-transform: uppercase;
  }

  .btn-group {
    display: flex;
    gap: 8px;
  }

  .btn {
    padding: 6px 12px;
    font-size: 0.8rem;
    font-weight: 700;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    cursor: pointer;
    box-shadow: 2px 2px 0px #121212;
    background: #ffffff;
    color: var(--rf-text-primary, #121212);
    transition: transform 0.1s;
  }

  .btn:hover {
    transform: translate(-1px, -1px);
    box-shadow: 3px 3px 0px #121212;
  }

  .btn.active {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
  }

  .main-viewport {
    display: flex;
    flex: 1;
    position: relative;
    overflow: hidden;
  }

  .canvas-container {
    flex: 1;
    position: relative;
    background: #f8f9fa;
    overflow: hidden;
    cursor: grab;
    user-select: none;
  }

  .canvas-container:active {
    cursor: grabbing;
  }

  .map-svg {
    width: 100%;
    height: 100%;
    position: absolute;
    top: 0;
    left: 0;
  }

  .territory-poly {
    fill-opacity: 0.25;
    stroke-width: 2px;
    stroke: #121212;
    transition: fill-opacity 0.2s;
  }

  .territory-poly:hover {
    fill-opacity: 0.45;
  }

  .territory-poly.contested {
    stroke: #e63946;
    stroke-dasharray: 6, 4;
    stroke-width: 3px;
  }

  .pin-marker {
    cursor: pointer;
    transition: transform 0.15s ease-out;
  }

  .pin-marker:hover {
    transform: scale(1.25);
  }

  .pin-dot {
    fill: var(--rf-accent-primary, #e63946);
    stroke: #121212;
    stroke-width: 2px;
  }

  .pin-label {
    font-size: 11px;
    font-weight: 800;
    fill: #121212;
    text-shadow: 1px 1px 0px #ffffff, -1px -1px 0px #ffffff;
    pointer-events: none;
  }

  .zoom-controls {
    position: absolute;
    bottom: 16px;
    left: 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    z-index: 5;
  }

  .zoom-btn {
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

  .drawer {
    width: 280px;
    background: #ffffff;
    border-left: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    display: flex;
    flex-direction: column;
    z-index: 10;
    overflow-y: auto;
  }

  .drawer-header {
    padding: 12px;
    font-weight: 800;
    font-size: 0.95rem;
    border-bottom: 2px solid #121212;
    background: #fafafa;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .drawer-content {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .filter-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .filter-label {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    color: #666;
  }

  .layer-selector {
    display: flex;
    gap: 4px;
  }

  .layer-btn {
    flex: 1;
    padding: 6px 4px;
    font-size: 0.75rem;
    font-weight: 700;
    border: 1px solid #121212;
    background: #ffffff;
    cursor: pointer;
    text-align: center;
  }

  .layer-btn.selected {
    background: #121212;
    color: #ffffff;
  }

  .era-input {
    padding: 6px 8px;
    font-size: 0.8rem;
    border: 1px solid #121212;
    font-family: inherit;
  }

  .codex-card {
    border: 1px solid #121212;
    padding: 10px;
    background: #fafafa;
    display: flex;
    flex-direction: column;
    gap: 4px;
    cursor: pointer;
  }

  .codex-card:hover {
    background: #f0f0f0;
  }

  .codex-card.selected {
    border: 2px solid #121212;
    box-shadow: 2px 2px 0px #121212;
    background: #ffffff;
  }

  .privacy-tag {
    font-size: 0.65rem;
    font-weight: 800;
    padding: 1px 6px;
    display: inline-block;
    width: fit-content;
    text-transform: uppercase;
  }

  .privacy-tag.private { background: #d90429; color: #fff; }
  .privacy-tag.party_shared { background: #2a9d8f; color: #fff; }
  .privacy-tag.public { background: #457b9d; color: #fff; }

  .entry-body {
    font-size: 0.8rem;
    line-height: 1.35;
    color: #333;
  }

  .entity-tag {
    font-size: 0.7rem;
    background: #e2eafc;
    border: 1px solid #121212;
    padding: 1px 4px;
    margin-right: 4px;
    font-weight: 600;
  }
`;
