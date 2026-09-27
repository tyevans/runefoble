import { css } from 'lit';

export const reactionPromptStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #121212);
    box-sizing: border-box;
  }
  .modal-backdrop {
    position: fixed; inset: 0;
    background: rgba(0, 0, 0, 0.75);
    display: flex; align-items: center; justify-content: center;
    z-index: var(--rf-z-modal, 1000);
    padding: 16px;
  }
  .modal-card {
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    width: 100%; max-width: 480px; padding: 20px;
    box-sizing: border-box;
  }
  .urgent-header {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 10px; margin-bottom: 12px;
  }
  .urgent-title {
    font-size: 1.15rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.05em; margin: 0; display: flex; align-items: center; gap: 8px;
  }
  .status-badge {
    font-size: 0.7rem; font-weight: 900; text-transform: uppercase;
    padding: 3px 8px; border: 1px solid var(--rf-border-color, #121212);
    background: var(--rf-accent-primary, #e63946); color: var(--rf-text-inverse, #ffffff);
  }
  .status-badge.resolved { background: #2a9d8f; }
  .status-badge.expired { background: #6c757d; }
  .timer-box { margin-bottom: 16px; }
  .timer-row {
    display: flex; justify-content: space-between; font-size: 0.8rem;
    font-weight: 800; text-transform: uppercase; margin-bottom: 4px;
  }
  .timer-countdown { font-family: ui-monospace, monospace; font-size: 1.1rem; }
  .timer-countdown.urgent { color: var(--rf-accent-primary, #e63946); animation: pulse 0.8s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  .countdown-track {
    height: 10px; background: var(--rf-bg-inset, #e9ecef);
    border: 1px solid var(--rf-border-color, #121212); overflow: hidden;
  }
  .countdown-fill {
    height: 100%; background: var(--rf-accent-secondary, #457b9d);
    transition: width 0.2s linear;
  }
  .countdown-fill.urgent { background: var(--rf-accent-primary, #e63946); }
  .trigger-banner {
    background: var(--rf-bg-inset, #f8f9fa);
    border-left: 4px solid var(--rf-accent-primary, #e63946);
    padding: 10px 12px; margin-bottom: 16px; font-size: 0.9rem;
  }
  .trigger-who { font-weight: 800; }
  .trigger-quote { font-style: italic; font-weight: 700; margin-top: 4px; color: var(--rf-text-secondary, #333); }
  .actions-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
  .btn-action {
    display: flex; justify-content: space-between; align-items: center;
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 10px 14px; font-weight: 800; font-size: 0.9rem; cursor: pointer;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212); text-align: left;
  }
  .btn-action:hover { background: var(--rf-accent-tertiary, #f1faee); }
  .btn-action:focus-visible { outline: 3px solid var(--rf-border-focus, #ffb703); }
  .btn-action.primary { background: var(--rf-accent-primary, #e63946); color: var(--rf-text-inverse, #ffffff); }
  .btn-action.primary:hover { opacity: 0.92; }
  .decline-btn {
    width: 100%; background: transparent; border: 1px solid var(--rf-border-color, #121212);
    padding: 8px; font-size: 0.8rem; font-weight: 800; text-transform: uppercase;
    cursor: pointer; color: var(--rf-text-secondary, #555);
  }
  .decline-btn:hover { background: #eee; }
  .resolution-toast {
    background: #e8f5e9; border: 2px solid #2e7d32; padding: 12px;
    font-weight: 800; text-align: center; color: #1b5e20;
  }
  .ready-card {
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    padding: 16px; width: 100%; max-width: 440px; box-sizing: border-box;
  }
  .form-group { margin-bottom: 10px; display: flex; flex-direction: column; gap: 4px; }
  .form-label { font-size: 0.75rem; font-weight: 800; text-transform: uppercase; }
  .form-input {
    border: 1px solid var(--rf-border-color, #121212); padding: 6px 8px;
    background: var(--rf-bg-inset, #f8f9fa); font-size: 0.85rem; font-weight: 600;
  }
  .armed-badge {
    background: #2a9d8f; color: #fff; padding: 2px 6px;
    font-size: 0.65rem; font-weight: 900; text-transform: uppercase;
  }
`;
