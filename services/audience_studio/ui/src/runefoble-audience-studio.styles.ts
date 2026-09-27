import { css } from 'lit';

export const audienceStudioStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, 'Space Grotesk', system-ui, sans-serif);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 16px;
    color: var(--rf-text-primary, #121212);
    width: 440px;
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
    font-size: 1.05rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    text-transform: uppercase;
  }

  .status-badge {
    padding: 3px 8px;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    border: 1px solid var(--rf-border-color, #121212);
  }

  .status-badge.live {
    background: var(--rf-accent-secondary, #2a9d8f);
    color: #ffffff;
  }

  .status-badge.offline {
    background: #e0e0e0;
    color: #555555;
  }

  .section {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px dashed var(--rf-border-color, #cccccc);
  }

  .section-title {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 8px;
    letter-spacing: 0.05em;
  }

  .poll-card {
    background: #fafafa;
    border: 1px solid #121212;
    padding: 12px;
    margin-bottom: 10px;
  }

  .poll-title {
    font-size: 0.95rem;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .poll-prompt {
    font-size: 0.85rem;
    color: #444;
    margin-bottom: 10px;
  }

  .option-row {
    margin-bottom: 8px;
  }

  .option-btn {
    display: flex;
    justify-content: space-between;
    width: 100%;
    padding: 8px 10px;
    background: #ffffff;
    border: 1px solid #121212;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 2px 2px 0px #121212;
    margin-bottom: 4px;
    font-family: inherit;
  }

  .option-btn:hover {
    background: #f0f0f0;
  }

  .progress-bar-bg {
    height: 6px;
    background: #eee;
    border: 1px solid #121212;
    overflow: hidden;
  }

  .progress-bar-fill {
    height: 100%;
    background: var(--rf-accent-primary, #e63946);
    transition: width 0.3s ease;
  }

  .proposal-card {
    background: #fff8e7;
    border: 1px solid #121212;
    padding: 10px;
    margin-bottom: 8px;
  }

  .btn-row {
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }

  .btn {
    flex: 1;
    padding: 6px 10px;
    font-size: 0.8rem;
    font-weight: 700;
    border: 1px solid #121212;
    cursor: pointer;
    box-shadow: 2px 2px 0px #121212;
    font-family: inherit;
    text-transform: uppercase;
  }

  .btn-approve {
    background: var(--rf-accent-secondary, #2a9d8f);
    color: #ffffff;
  }

  .btn-veto {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
  }
`;
