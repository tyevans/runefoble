import { css } from 'lit';

export const assignmentDialogStyles = css`
  .empty-roster {
    grid-column: 1 / -1;
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) dashed var(--rf-border-color, rgb(18, 18, 18));
    padding: 48px 24px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .empty-icon {
    font-size: 2.5rem;
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

  .assign-dialog {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 6px 6px 0px rgb(18, 18, 18));
    width: 100%;
    max-width: 440px;
    padding: 20px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .dialog-title {
    font-size: 1.15rem;
    font-weight: 900;
    text-transform: uppercase;
    margin: 0;
  }

  .dialog-select {
    padding: 8px 10px;
    font-size: 0.9rem;
    font-weight: 600;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
    font-family: inherit;
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 8px;
  }
`;
