import { css } from 'lit';

export const dmWhisperBarStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary);
    background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow);
    padding: 16px;
    box-sizing: border-box;
    width: 100%;
    max-width: 800px;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
    padding-bottom: 10px;
    margin-bottom: 12px;
  }

  .title-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .title-group h3 {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: -0.01em;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    font-size: 0.7rem;
    font-weight: 800;
    text-transform: uppercase;
    padding: 3px 8px;
    border: 1px solid var(--rf-border-color);
    letter-spacing: 0.04em;
  }

  .badge-dm {
    background: var(--rf-accent-secondary);
    color: var(--rf-text-inverse);
  }

  .badge-whisper-type {
    background: var(--rf-accent-tertiary);
    color: var(--rf-text-primary);
  }

  .badge-pending {
    background: var(--rf-accent-primary);
    color: var(--rf-text-inverse);
    animation: pulse 1.5s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }

  /* Pending Action Interceptor Banner */
  .interceptor-box {
    background: var(--rf-bg-canvas);
    border: 2px solid var(--rf-accent-primary);
    padding: 12px;
    margin-bottom: 16px;
    position: relative;
  }

  .interceptor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .interceptor-title {
    font-weight: 800;
    font-size: 0.95rem;
    color: var(--rf-accent-primary);
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .countdown-bar {
    width: 100%;
    height: 6px;
    background: var(--rf-bg-inset);
    margin-bottom: 10px;
    overflow: hidden;
  }

  .countdown-fill {
    height: 100%;
    background: var(--rf-accent-primary);
    transition: width 0.1s linear;
  }

  .action-details {
    font-size: 0.88rem;
    line-height: 1.4;
    margin-bottom: 12px;
  }

  .action-actor {
    font-weight: 700;
  }

  .action-controls {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .rf-btn {
    font-family: inherit;
    font-size: 0.8rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 6px 14px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    cursor: pointer;
    box-shadow: 2px 2px 0px 0px var(--rf-shadow-color);
    transition: transform 0.05s ease, box-shadow 0.05s ease;
  }

  .rf-btn:hover {
    transform: translate(-1px, -1px);
    box-shadow: 3px 3px 0px 0px var(--rf-shadow-color);
  }

  .rf-btn:active {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px 0px var(--rf-shadow-color);
  }

  .btn-approve {
    background: var(--rf-accent-secondary);
    color: var(--rf-text-inverse);
  }

  .btn-veto {
    background: var(--rf-accent-primary);
    color: var(--rf-text-inverse);
  }

  .btn-edit {
    background: var(--rf-accent-tertiary);
    color: var(--rf-text-primary);
  }

  /* Inline Edit Form */
  .edit-form {
    margin-top: 10px;
    padding: 10px;
    background: var(--rf-bg-card);
    border: 1px solid var(--rf-border-color);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .form-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .form-row label {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
  }

  .form-row input {
    font-family: inherit;
    font-size: 0.85rem;
    padding: 4px 8px;
    border: 1px solid var(--rf-border-color);
  }

  /* Whisper Stream Section */
  .whisper-section {
    margin-top: 12px;
  }

  .section-title {
    font-weight: 800;
    font-size: 0.9rem;
    text-transform: uppercase;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .filter-tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 8px;
  }

  .tab-btn {
    font-family: inherit;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 3px 8px;
    border: 1px solid var(--rf-border-color);
    background: var(--rf-bg-surface);
    cursor: pointer;
  }

  .tab-btn.active {
    background: var(--rf-border-color);
    color: var(--rf-text-inverse);
  }

  .whisper-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 240px;
    overflow-y: auto;
  }

  .whisper-card {
    background: var(--rf-bg-canvas);
    border: 1px solid var(--rf-border-color);
    padding: 8px 12px;
  }

  .whisper-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }

  .whisper-content {
    font-size: 0.85rem;
    line-height: 1.4;
  }

  .whisper-notice {
    margin-top: 6px;
    padding: 6px 8px;
    border: 1px dashed var(--rf-border-color);
    font-size: 0.8rem;
    color: var(--rf-text-muted);
  }

  .whisper-actions {
    margin-top: 6px;
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .sent-badge {
    font-size: 0.75rem;
    color: var(--rf-status-success);
    font-weight: 600;
  }

  .empty-state {
    font-size: 0.85rem;
    color: var(--rf-text-muted);
    font-style: italic;
    padding: 12px 0;
    text-align: center;
  }
`;
