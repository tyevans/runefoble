import { css } from 'lit';

export const settingsStyles = css`
  :host {
    display: block;
    margin-top: 8px;
  }
  .settings-card {
    background: var(--rf-bg-canvas, #f4f4f5);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #111111);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgba(0, 0, 0, 0.9));
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.85rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .control-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .control-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--rf-text-primary, #111111);
  }
  .val-badge {
    font-family: monospace;
    font-weight: 700;
    padding: 1px 5px;
    background: var(--rf-bg-surface, #ffffff);
    border: 1px solid var(--rf-border-color, #111111);
    font-size: 0.72rem;
  }
  input[type='range'] {
    width: 100%;
    accent-color: var(--rf-accent-primary, #ef4444);
    cursor: pointer;
  }
  .checkbox-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
    font-weight: 700;
    cursor: pointer;
  }
  input[type='checkbox'] {
    width: 16px;
    height: 16px;
    accent-color: var(--rf-accent-secondary, #22c55e);
    cursor: pointer;
  }
`;
