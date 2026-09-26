import { css } from 'lit';

export const settingsModalControlsStyles = css`
  .swatch-group {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: auto;
  }

  .swatch-chip {
    width: 18px;
    height: 18px;
    border: 1px solid var(--rf-border-color);
    box-sizing: border-box;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .form-label {
    font-size: 0.82rem;
    font-weight: 700;
  }

  .form-select {
    padding: 8px 12px;
    font-size: 0.85rem;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    background: var(--rf-bg-surface);
    color: var(--rf-text-primary);
    box-shadow: var(--rf-shadow-sm);
  }

  .form-select:focus {
    outline: none;
    border-color: var(--rf-border-focus, var(--rf-accent-primary));
  }

  .checkbox-row {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
  }

  .checkbox-row input[type="checkbox"] {
    cursor: pointer;
  }

  .slider-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .slider-control {
    width: 100%;
    accent-color: var(--rf-accent-primary);
  }

  .typography-preview {
    font-family: var(--rf-font-family, system-ui, sans-serif);
    font-size: 0.85rem;
    color: var(--rf-text-secondary);
  }
`;

export const controlsStyles = settingsModalControlsStyles;
