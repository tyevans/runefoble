import { css } from 'lit';

export const modalStyles = css`
  /* Modals & Dialogs */
  .modal-backdrop {
    position: fixed; inset: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex; align-items: center; justify-content: center;
    z-index: var(--rf-z-modal, 1000);
    padding: 16px;
  }

  .modal-card {
    background: var(--rf-bg-surface-elevated, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 6px 6px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    width: 100%; max-width: 480px; padding: 24px;
  }

  .modal-header {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding-bottom: 12px; margin-bottom: 18px;
  }

  .modal-title {
    font-size: 1.2rem; font-weight: 900; margin: 0;
    text-transform: uppercase; letter-spacing: 0.03em;
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .modal-desc {
    font-size: 0.95rem; line-height: 1.5;
    color: var(--rf-text-primary, rgb(18, 18, 18));
    margin: 0 0 16px;
  }

  .btn-close {
    background: transparent;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    width: 30px; height: 30px; font-weight: 900; font-size: 1rem;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .btn-close:hover {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
  }

  .form-group {
    margin-bottom: 16px;
    display: flex; flex-direction: column; gap: 6px;
  }

  .form-label {
    font-size: 0.8rem; font-weight: 800;
    text-transform: uppercase; letter-spacing: 0.04em;
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .form-select,
  .form-input {
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding: 8px 12px;
    background: var(--rf-bg-inset, rgb(248, 249, 250));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    font-family: inherit; font-size: 0.9rem; font-weight: 600; outline: none;
  }

  .invite-link-row {
    display: flex; gap: 8px; align-items: center; margin-top: 10px;
  }

  .invite-link-input {
    flex: 1; font-family: monospace; font-size: 0.8rem;
    background: var(--rf-bg-inset, rgb(241, 250, 238));
  }

  .btn-copy {
    background: var(--rf-accent-secondary, rgb(29, 53, 87));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 8px 14px; font-weight: 800; font-size: 0.8rem;
    cursor: pointer; text-transform: uppercase; white-space: nowrap;
    transition: transform 0.1s ease;
  }

  .btn-copy:hover {
    transform: translate(-1px, -1px);
  }

  .copied-badge {
    display: inline-block;
    color: var(--rf-accent-tertiary, rgb(255, 183, 3));
    font-weight: 800; font-size: 0.75rem; margin-top: 4px;
  }

  .modal-actions {
    display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px;
    border-top: 1px solid var(--rf-border-subtle, rgba(18, 18, 18, 0.15));
    padding-top: 16px;
  }

  .btn-cancel {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 8px 16px; font-weight: 800; font-size: 0.85rem;
    cursor: pointer; text-transform: uppercase;
  }

  .btn-confirm-remove {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 8px 18px; font-weight: 900; font-size: 0.85rem;
    cursor: pointer; text-transform: uppercase;
  }
`;
