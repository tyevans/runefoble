import { css } from 'lit';

export const mapUploaderStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #121212);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    border-radius: var(--rf-border-radius, 0px);
    padding: 16px;
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    box-sizing: border-box;
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    flex-wrap: wrap;
    gap: 12px;
  }

  .title {
    font-size: 1.15rem;
    font-weight: 800;
    color: var(--rf-text-primary, #121212);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .actions-bar {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .btn {
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    border-radius: var(--rf-border-radius, 0px);
    padding: 6px 12px;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    transition: all 0.15s ease-in-out;
  }

  .btn:hover {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
  }

  .btn:active {
    transform: translate(1px, 1px);
    box-shadow: none;
  }

  .btn-primary {
    background: var(--rf-accent-tertiary, #ffb703);
    color: var(--rf-color-dark, #121212);
  }

  .btn-danger {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
  }

  .dropzone {
    border: 3px dashed var(--rf-border-color, #121212);
    background: var(--rf-bg-canvas, #f8f9fa);
    padding: 36px 16px;
    text-align: center;
    cursor: pointer;
    transition: background-color 0.2s ease, border-color 0.2s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }

  .dropzone.dragging {
    background: rgba(255, 183, 3, 0.15);
    border-color: var(--rf-accent-tertiary, #ffb703);
  }

  .drop-icon {
    font-size: 2.2rem;
  }

  .drop-title {
    font-size: 1rem;
    font-weight: 800;
  }

  .drop-hint {
    font-size: 0.75rem;
    color: var(--rf-text-muted, #4b5563);
  }

  .progress-section {
    margin-top: 16px;
    padding: 12px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    background: var(--rf-bg-canvas, #f8f9fa);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
  }

  .progress-header {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 6px;
  }

  .progress-bar-container {
    width: 100%;
    height: 12px;
    background: #ffffff;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    overflow: hidden;
  }

  .progress-bar-fill {
    height: 100%;
    background: var(--rf-accent-primary, #e63946);
    transition: width 0.2s ease-in-out;
  }

  .preview-container {
    position: relative;
    width: 100%;
    max-width: 720px;
    margin: 0 auto;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    overflow: hidden;
    background: #000000;
  }

  .preview-image {
    display: block;
    width: 100%;
    height: auto;
    user-select: none;
    pointer-events: none;
  }

  .shroud-overlay {
    position: absolute;
    inset: 0;
    display: grid;
    pointer-events: auto;
  }

  .shroud-cell {
    box-sizing: border-box;
    border: 1px solid rgba(255, 255, 255, 0.25);
    cursor: pointer;
    position: relative;
    transition: background-color 0.15s ease;
  }

  .shroud-cell.shrouded {
    background: repeating-linear-gradient(
      45deg,
      rgba(18, 18, 18, 0.95),
      rgba(18, 18, 18, 0.95) 6px,
      rgba(30, 30, 30, 0.95) 6px,
      rgba(30, 30, 30, 0.95) 12px
    );
  }

  .shroud-cell.revealed {
    background: transparent;
  }

  .shroud-cell:hover {
    outline: 2px solid var(--rf-accent-tertiary, #ffb703);
    z-index: 5;
  }

  .controls-panel {
    margin-top: 16px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    padding: 12px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    background: var(--rf-bg-canvas, #f8f9fa);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
  }

  .slider-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .slider-group label {
    font-size: 0.75rem;
    font-weight: 700;
    display: flex;
    justify-content: space-between;
  }

  .slider-group input[type='range'] {
    accent-color: var(--rf-accent-primary, #e63946);
    cursor: pointer;
  }

  .status-msg {
    margin-top: 8px;
    padding: 6px 10px;
    font-size: 0.8rem;
    font-weight: 700;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
  }

  .status-msg.error {
    background: #ffe5e5;
    color: #b91c1c;
  }

  .status-msg.success {
    background: #e6f9ed;
    color: #15803d;
  }
`;
