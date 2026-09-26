import { css } from 'lit';

export const assetForgeStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    border-radius: var(--rf-border-radius, 0px);
    padding: 16px;
    color: var(--rf-text-primary, #121212);
    width: 520px;
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
    font-size: 1.1rem;
    font-weight: 800;
    letter-spacing: -0.02em;
  }
  .tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 14px;
  }
  .tab-btn {
    flex: 1;
    padding: 6px 12px;
    font-size: 0.8rem;
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
  .input-field {
    padding: 8px 10px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    font-family: inherit;
    font-size: 0.85rem;
    box-sizing: border-box;
  }
  .row {
    display: flex;
    gap: 8px;
  }
  .submit-btn {
    padding: 10px 16px;
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
    font-weight: 800;
    font-size: 0.9rem;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    cursor: pointer;
    box-shadow: 2px 2px 0px #121212;
    margin-top: 6px;
    width: 100%;
  }
  .submit-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .preview-card {
    margin-top: 14px;
    border: 1px solid var(--rf-border-color, #121212);
    padding: 12px;
    background: #fafafa;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .preview-image {
    width: 100%;
    max-height: 240px;
    object-fit: contain;
    border: 1px solid var(--rf-border-color, #121212);
    background: #222;
  }
  .stats-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 0.75rem;
  }
  .stat-badge {
    padding: 2px 6px;
    background: var(--rf-accent-tertiary, #ffb703);
    border: 1px solid var(--rf-border-color, #121212);
    font-weight: 700;
  }
  .action-btn {
    padding: 6px 12px;
    font-weight: 700;
    font-size: 0.8rem;
    background: #121212;
    color: #fff;
    border: none;
    cursor: pointer;
  }
`;
