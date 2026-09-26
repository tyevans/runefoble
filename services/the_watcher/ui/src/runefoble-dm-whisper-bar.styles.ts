import { css } from 'lit';

export const dmWhisperBarStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #111827);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #111827);
    box-shadow: var(--rf-shadow, 4px 4px 0px 0px rgba(0, 0, 0, 1));
    padding: 16px;
    box-sizing: border-box;
    width: 100%;
    max-width: 800px;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #111827);
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
    border: 1px solid var(--rf-border-color, #111827);
    letter-spacing: 0.04em;
  }

  .badge-dm {
    background: var(--rf-accent-secondary, #2563eb);
    color: var(--rf-text-inverse, #ffffff);
  }

  .badge-whisper-type {
    background: var(--rf-accent-tertiary, #eab308);
    color: var(--rf-text-primary, #111827);
  }

  .badge-pending {
    background: var(--rf-accent-primary, #dc2626);
    color: var(--rf-text-inverse, #ffffff);
    animation: pulse 1.5s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }

  /* Pending Action Interceptor Banner */
  .interceptor-box {
    background: var(--rf-bg-canvas, #f3f4f6);
    border: 2px solid var(--rf-accent-primary, #dc2626);
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
    color: var(--rf-accent-primary, #dc2626);
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .countdown-bar {
    width: 100%;
    height: 6px;
    background: #e5e7eb;
    margin-bottom: 10px;
    overflow: hidden;
  }

  .countdown-fill {
    height: 100%;
    background: var(--rf-accent-primary, #dc2626);
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
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #111827);
    cursor: pointer;
    box-shadow: 2px 2px 0px 0px rgba(0, 0, 0, 1);
    transition: transform 0.05s ease, box-shadow 0.05s ease;
  }

  .rf-btn:hover {
    transform: translate(-1px, -1px);
    box-shadow: 3px 3px 0px 0px rgba(0, 0, 0, 1);
  }

  .rf-btn:active {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px 0px rgba(0, 0, 0, 1);
  }

  .btn-approve {
    background: var(--rf-accent-secondary, #2563eb);
    color: var(--rf-text-inverse, #ffffff);
  }

  .btn-veto {
    background: var(--rf-accent-primary, #dc2626);
    color: var(--rf-text-inverse, #ffffff);
  }

  .btn-edit {
    background: var(--rf-accent-tertiary, #eab308);
    color: var(--rf-text-primary, #111827);
  }

  /* Inline Edit Form */
  .edit-form {
    margin-top: 10px;
    padding: 10px;
    background: #ffffff;
    border: 1px solid var(--rf-border-color, #111827);
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
    border: 1px solid var(--rf-border-color, #111827);
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
    border: 1px solid var(--rf-border-color, #111827);
    background: var(--rf-bg-surface, #ffffff);
    cursor: pointer;
  }

  .tab-btn.active {
    background: var(--rf-border-color, #111827);
    color: var(--rf-text-inverse, #ffffff);
  }

  .whisper-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 240px;
    overflow-y: auto;
  }

  .whisper-card {
    background: var(--rf-bg-canvas, #f3f4f6);
    border: 1px solid var(--rf-border-color, #111827);
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

  .empty-state {
    font-size: 0.85rem;
    color: #6b7280;
    font-style: italic;
    padding: 12px 0;
    text-align: center;
  }
`;
