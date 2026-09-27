import { css } from 'lit';

export const characterBuilderModalStyles = css`
  :host {
    display: contents;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
  }

  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.75);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: var(--rf-z-modal, 1000);
    padding: 16px;
    box-sizing: border-box;
  }

  .modal-dialog {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 6px 6px 0px rgb(18, 18, 18));
    border-radius: var(--rf-border-radius, 0px);
    width: 100%;
    max-width: 580px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
    overflow: hidden;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 18px;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-canvas, rgb(248, 249, 250));
  }

  .modal-title {
    font-size: 1.15rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: -0.3px;
    margin: 0;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    font-weight: 800;
    cursor: pointer;
    line-height: 1;
    color: var(--rf-text-primary, rgb(18, 18, 18));
    padding: 0 4px;
  }
  .close-btn:hover {
    color: var(--rf-accent-primary, rgb(230, 57, 70));
  }

  .modal-body {
    padding: 18px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
    box-sizing: border-box;
  }

  .error-banner {
    background: rgb(253, 232, 232);
    color: var(--rf-accent-primary, rgb(230, 57, 70));
    border: 2px solid var(--rf-accent-primary, rgb(230, 57, 70));
    padding: 8px 12px;
    font-size: 0.85rem;
    font-weight: 700;
  }

  .form-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
    min-width: 120px;
  }

  .form-group label {
    font-size: 0.78rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--rf-text-muted, rgb(75, 85, 99));
  }

  .form-input,
  .form-select {
    padding: 8px 10px;
    font-size: 0.9rem;
    font-weight: 600;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
    box-sizing: border-box;
    font-family: inherit;
  }

  .form-input:focus,
  .form-select:focus {
    outline: none;
    border-color: var(--rf-accent-secondary, rgb(29, 53, 87));
  }

  .ability-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 8px;
  }
  @media (max-width: 500px) {
    .ability-grid {
      grid-template-columns: repeat(3, 1fr);
    }
  }

  .ability-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-canvas, rgb(248, 249, 250));
    padding: 6px 4px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
  }

  .ability-label {
    font-size: 0.7rem;
    font-weight: 900;
    text-transform: uppercase;
  }

  .ability-input {
    width: 100%;
    max-width: 44px;
    text-align: center;
    padding: 4px;
    font-weight: 800;
    font-size: 0.9rem;
    border: 1px solid var(--rf-border-color, rgb(18, 18, 18));
    margin: 4px 0;
  }

  .ability-mod {
    font-size: 0.75rem;
    font-weight: 800;
    color: var(--rf-accent-secondary, rgb(29, 53, 87));
  }

  .portrait-options {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    margin-top: 4px;
  }

  .portrait-btn {
    width: 44px;
    height: 44px;
    border: 2px solid var(--rf-border-color, rgb(18, 18, 18));
    padding: 2px;
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    cursor: pointer;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
    transition: transform 0.1s ease;
  }
  .portrait-btn:hover {
    transform: translate(-1px, -1px);
  }
  .portrait-btn.selected {
    border-color: var(--rf-accent-primary, rgb(230, 57, 70));
    box-shadow: 0 0 0 2px var(--rf-accent-primary, rgb(230, 57, 70));
  }
  .portrait-btn img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 14px 18px;
    border-top: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-canvas, rgb(248, 249, 250));
  }

  .btn {
    padding: 8px 16px;
    font-size: 0.85rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    cursor: pointer;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .btn:hover {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow, 4px 4px 0px rgb(18, 18, 18));
  }
  .btn:active {
    transform: translate(1px, 1px);
    box-shadow: none;
  }
  .btn-cancel {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }
  .btn-submit {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: rgb(255, 255, 255);
  }
`;
