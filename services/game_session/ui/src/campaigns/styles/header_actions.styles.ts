import { css } from 'lit';

export const headerActionsStyles = css`
  /* Title & Action Row */
  .title-action-row {
    display: flex; justify-content: space-between; align-items: flex-start;
    gap: 16px; flex-wrap: wrap;
  }

  .btn-edit-campaign {
    background: var(--rf-accent-primary, rgb(230, 57, 70)); color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 7px 16px; font-weight: 800; font-size: 0.82rem; cursor: pointer;
    text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap;
    display: inline-flex; align-items: center; gap: 6px;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }

  .btn-edit-campaign:hover {
    transform: translate(-1px, -1px); box-shadow: 3px 3px 0px var(--rf-shadow-color, rgb(18, 18, 18));
  }

  /* Modal Dialog */
  .modal-backdrop {
    position: fixed; inset: 0; padding: 16px;
    background: rgba(0, 0, 0, 0.7); z-index: var(--rf-z-modal, 1000);
    display: flex; align-items: center; justify-content: center;
  }

  .modal-card {
    background: var(--rf-bg-surface-elevated, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 6px 6px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    width: 100%; max-width: 520px; padding: 24px; max-height: 90vh; overflow-y: auto;
  }

  .modal-header {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding-bottom: 12px; margin-bottom: 20px;
  }

  .modal-title {
    font-size: 1.25rem; font-weight: 900; margin: 0;
    text-transform: uppercase; letter-spacing: 0.03em;
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .btn-close {
    background: transparent; color: var(--rf-text-primary, rgb(18, 18, 18));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    width: 32px; height: 32px; font-weight: 900; font-size: 1.1rem; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: transform 0.1s ease, background 0.1s ease;
  }

  .btn-close:hover {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255)); transform: translate(-1px, -1px);
  }

  .form-group {
    margin-bottom: 16px; display: flex; flex-direction: column; gap: 6px;
  }

  .form-label {
    font-size: 0.8rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.04em; color: var(--rf-text-primary, rgb(18, 18, 18));
    display: flex; align-items: center; gap: 4px;
  }

  .required-star { color: var(--rf-accent-primary, rgb(230, 57, 70)); }

  .form-input,
  .form-select,
  .form-textarea {
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding: 10px 12px; background: var(--rf-bg-inset, rgb(248, 249, 250));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    font-family: inherit; font-size: 0.9rem; font-weight: 600;
    width: 100%; outline: none; transition: border-color 0.15s ease;
  }

  .form-input:focus,
  .form-select:focus,
  .form-textarea:focus { border-color: var(--rf-border-focus, rgb(255, 183, 3)); }

  .form-textarea { min-height: 80px; resize: vertical; }

  .error-banner {
    background: rgba(230, 57, 70, 0.12); color: var(--rf-accent-primary, rgb(230, 57, 70));
    border: var(--rf-border-width, 2px) solid var(--rf-accent-primary, rgb(230, 57, 70));
    padding: 10px 14px; font-weight: 800; font-size: 0.85rem;
    margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
  }

  .modal-actions {
    display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; padding-top: 18px;
    border-top: 1px solid var(--rf-border-subtle, rgba(18, 18, 18, 0.15));
  }

  .btn-cancel {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 9px 18px; font-weight: 800; font-size: 0.9rem; cursor: pointer;
    color: var(--rf-text-primary, rgb(18, 18, 18)); text-transform: uppercase; letter-spacing: 0.03em;
  }

  .btn-cancel:hover { background: var(--rf-bg-inset, rgb(241, 250, 238)); }

  .btn-submit {
    background: var(--rf-accent-primary, rgb(230, 57, 70)); color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 9px 22px; font-weight: 900; font-size: 0.9rem; cursor: pointer;
    text-transform: uppercase; letter-spacing: 0.04em;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }

  .btn-submit:hover:not(:disabled) {
    transform: translate(-1px, -1px); box-shadow: 3px 3px 0px var(--rf-shadow-color, rgb(18, 18, 18));
  }

  .btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }
`;
