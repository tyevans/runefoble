import { css } from 'lit';

/** Take a Seat panel of the lobby (TASK-0889). */
export const seatStyles = css`
  .seat-panel {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: 12px;
    padding: 16px;
    margin-bottom: 20px;
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 4px 4px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
  }
  .seat-panel .char-select-container {
    flex: 1 1 220px;
  }
  .seat-hint {
    flex: 1 1 100%;
    margin: 0;
    font-size: 0.85rem;
    color: var(--rf-text-secondary, rgb(43, 45, 66));
  }
  .btn-take-seat {
    background: var(--rf-accent-secondary, rgb(29, 53, 87));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: 3px 3px 0px var(--rf-shadow-color, rgb(18, 18, 18));
    padding: 10px 20px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    cursor: pointer;
  }
  .btn-take-seat:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;
