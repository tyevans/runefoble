import { css } from 'lit';

export const controlsStyles = css`
  /* Readiness Badges */
  .badge-readiness {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 4px 8px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    white-space: nowrap;
  }
  .badge-ready {
    background: rgb(34, 197, 94);
    color: rgb(255, 255, 255);
  }
  .badge-setting-up {
    background: var(--rf-accent-tertiary, rgb(255, 183, 3));
    color: rgb(18, 18, 18);
  }
  .badge-standin {
    background: rgb(168, 85, 247);
    color: rgb(255, 255, 255);
  }

  /* Character Selector Dropdown */
  .char-select-container {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .select-label {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--rf-text-secondary, rgb(43, 45, 66));
  }
  .character-dropdown {
    width: 100%;
    padding: 8px 10px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    font-family: inherit;
    font-size: 0.85rem;
    font-weight: 700;
    cursor: pointer;
  }
  .character-dropdown:focus {
    outline: none;
    border-color: var(--rf-border-focus, rgb(29, 53, 87));
  }

  /* Participant Controls / Checkboxes */
  .card-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--rf-border-subtle, rgba(18, 18, 18, 0.15));
  }
  .control-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.82rem;
    font-weight: 700;
    cursor: pointer;
    color: var(--rf-text-primary, rgb(18, 18, 18));
    user-select: none;
  }
  .control-toggle input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--rf-accent-primary, rgb(230, 57, 70));
    cursor: pointer;
  }
`;
