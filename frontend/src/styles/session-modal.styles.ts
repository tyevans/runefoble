import { css } from 'lit';

export const sessionModalStyles = css`
  :host {
    display: contents;
  }
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: var(--rf-z-modal, 1000);
    padding: 16px;
  }
  .modal-card {
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    width: 100%;
    max-width: 520px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 12px;
  }
  .modal-title {
    font-size: 1.25rem;
    font-weight: 800;
    margin: 0;
    color: var(--rf-text-primary, #121212);
    letter-spacing: -0.3px;
  }
  .btn-close {
    background: none;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    cursor: pointer;
    font-size: 1.2rem;
    font-weight: 800;
    padding: 2px 8px;
    line-height: 1;
    color: var(--rf-text-primary, #121212);
    transition: transform 0.1s ease;
  }
  .btn-close:hover {
    transform: translate(-1px, -1px);
  }
  form {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  label {
    font-size: 0.82rem;
    font-weight: 800;
    text-transform: uppercase;
    color: var(--rf-text-primary, #121212);
    letter-spacing: 0.5px;
  }
  .required {
    color: var(--rf-accent-primary, #e63946);
  }
  input,
  select,
  textarea {
    padding: 8px 10px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    background: var(--rf-bg-canvas, #ffffff);
    color: var(--rf-text-primary, #121212);
    font-size: 0.95rem;
    font-family: inherit;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
  }
  input:focus,
  select:focus,
  textarea:focus {
    outline: none;
    border-color: var(--rf-accent-secondary, #1d3557);
  }
  textarea {
    resize: vertical;
    min-height: 70px;
  }
  .error-banner {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
    padding: 8px 12px;
    font-size: 0.85rem;
    font-weight: 700;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 8px;
  }
  .btn-cancel {
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    font-weight: 800;
    font-size: 0.85rem;
    padding: 8px 16px;
    cursor: pointer;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .btn-cancel:hover {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
  }
  .btn-submit {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    font-weight: 800;
    font-size: 0.85rem;
    padding: 8px 18px;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .btn-submit:hover:not(:disabled) {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
  }
  .btn-submit:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;
