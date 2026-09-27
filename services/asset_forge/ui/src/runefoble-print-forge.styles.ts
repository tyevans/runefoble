import { css } from 'lit';

export const printForgeStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 16px;
    color: var(--rf-text-primary, #121212);
    width: 560px;
    max-width: 100%;
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    box-sizing: border-box;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 8px;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    margin-bottom: 12px;
  }
  .title {
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: -0.02em;
  }
  .badge {
    font-size: 0.7rem;
    font-weight: 700;
    background: #121212;
    color: #ffffff;
    padding: 2px 6px;
    text-transform: uppercase;
  }
  .tabs {
    display: flex;
    gap: 6px;
    margin-bottom: 14px;
  }
  .tab-btn {
    flex: 1;
    padding: 8px 10px;
    font-size: 0.75rem;
    font-weight: 700;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    background: #f0f0f0;
    cursor: pointer;
  }
  .tab-btn.active {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
    box-shadow: 2px 2px 0px #121212;
  }
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 10px;
  }
  .form-label {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
  }
  .input-field, .select-field {
    padding: 8px 10px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    font-family: inherit;
    font-size: 0.85rem;
    box-sizing: border-box;
    background: #ffffff;
  }
  .row {
    display: flex;
    gap: 8px;
  }
  .action-btn {
    padding: 10px 16px;
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
    font-weight: 800;
    font-size: 0.85rem;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    cursor: pointer;
    box-shadow: 2px 2px 0px #121212;
    margin-top: 8px;
    width: 100%;
    transition: transform 0.1s ease;
  }
  .action-btn:hover {
    transform: translate(-1px, -1px);
  }
  .action-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .preview-panel {
    margin-top: 14px;
    border: 1px solid var(--rf-border-color, #121212);
    padding: 12px;
    background: #fafafa;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }
  .preview-svg {
    border: 1px dashed #888888;
    background: #ffffff;
    width: 100%;
    max-height: 180px;
  }
  .preview-stats {
    font-size: 0.75rem;
    color: #444444;
    text-align: center;
    line-height: 1.4;
  }
`;
