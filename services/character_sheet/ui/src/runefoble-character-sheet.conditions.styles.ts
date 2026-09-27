import { css } from 'lit';

export const characterSheetConditionsStyles = css`
  /* Conditions & Absence Penalties */
  .conditions-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 14px;
    position: relative;
  }

  .condition-badge {
    position: relative;
    cursor: pointer;
    font-size: 0.78rem;
    font-weight: 700;
    padding: 4px 10px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    display: inline-flex;
    align-items: center;
    gap: 6px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    user-select: none;
    transition: transform 0.1s ease;
  }
  .condition-badge:hover { transform: translateY(-1px); }
  .condition-badge.tactical { background: var(--rf-accent-secondary, #1d3557); color: var(--rf-text-inverse, #ffffff); }
  .condition-badge.penalty { background: var(--rf-accent-tertiary, #ffb703); color: var(--rf-color-dark, #121212); }

  .remove-condition-btn {
    border: none;
    background: transparent;
    color: inherit;
    font-weight: 900;
    font-size: 0.8rem;
    cursor: pointer;
    padding: 0 0 0 4px;
  }

  /* Tooltip overlay */
  .condition-tooltip {
    position: absolute;
    bottom: calc(100% + 8px);
    left: 0;
    z-index: 50;
    background: var(--rf-color-dark, #121212);
    color: var(--rf-text-inverse, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-accent-tertiary, #ffb703);
    padding: 10px 12px;
    font-size: 0.78rem;
    width: 260px;
    box-shadow: 4px 4px 0px rgba(0, 0, 0, 0.4);
    line-height: 1.4;
    pointer-events: none;
  }

  .tooltip-title {
    font-weight: 800;
    color: var(--rf-accent-tertiary, #ffb703);
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
  }

  .tooltip-detail {
    font-size: 0.72rem;
    margin-top: 4px;
    color: #e2e8f0;
  }

  /* Spell Slots & Spellbook */
  .spell-tier-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 8px;
    background: var(--rf-bg-canvas, #f8f9fa);
    border: 1px solid var(--rf-border-color, #121212);
    margin-bottom: 6px;
  }

  .tier-label { font-size: 0.78rem; font-weight: 700; }

  .pips-container {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .spell-pip {
    width: 18px;
    height: 18px;
    border: 2px solid var(--rf-border-color, #121212);
    border-radius: 50%;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--rf-accent-secondary, #1d3557);
    color: var(--rf-text-inverse, #ffffff);
    font-size: 0.7rem;
    transition: transform 0.15s ease, background-color 0.2s ease;
  }
  .spell-pip:hover { transform: scale(1.15); }
  .spell-pip.expended { background: var(--rf-bg-surface, #ffffff); color: transparent; }

  .spell-list {
    list-style: none;
    padding: 0;
    margin: 8px 0 0 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .spell-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--rf-bg-inset, #f1f3f5);
    border: 1px solid var(--rf-border-subtle, #d1d5db);
    padding: 5px 8px;
    font-size: 0.82rem;
    font-weight: 600;
  }

  .spell-tags {
    display: flex;
    gap: 4px;
    align-items: center;
  }

  .spell-badge-prepared {
    background: var(--rf-accent-secondary, #1d3557);
    color: var(--rf-text-inverse, #ffffff);
    font-size: 0.65rem;
    font-weight: 700;
    padding: 1px 5px;
    text-transform: uppercase;
  }

  /* Responsive Breakpoints */
  @media (max-width: 680px) {
    .columns-layout { grid-template-columns: 1fr; }
    .vitals-grid { grid-template-columns: repeat(2, 1fr); }
  }
`;

export const conditionsStyles = characterSheetConditionsStyles;
