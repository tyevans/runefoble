import { css } from 'lit';

export const characterSheetStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-card, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    border-radius: var(--rf-border-radius, 0px);
    padding: 20px;
    color: var(--rf-text-primary, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px var(--rf-shadow-color, #121212));
    box-sizing: border-box;
    width: 100%;
    max-width: 860px;
  }

  .sheet-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 12px;
    margin-bottom: 16px;
    gap: 12px;
  }

  .char-identity h1 {
    font-size: 1.5rem;
    font-weight: 800;
    margin: 0 0 4px 0;
    letter-spacing: -0.02em;
  }

  .char-meta {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--rf-text-muted, #4b5563);
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .badge-stand-in {
    background: var(--rf-accent-tertiary, #ffb703);
    color: var(--rf-color-dark, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    font-size: 0.75rem;
    font-weight: 800;
    padding: 2px 8px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    text-transform: uppercase;
  }

  /* Core Stats Row */
  .vitals-grid {
    display: grid;
    grid-template-columns: 2fr repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 18px;
  }

  .vital-card {
    background: var(--rf-bg-canvas, #f8f9fa);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 8px 12px;
    text-align: center;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
  }

  .vital-label {
    font-size: 0.7rem;
    font-weight: 800;
    text-transform: uppercase;
    color: var(--rf-text-muted, #4b5563);
    margin-bottom: 2px;
  }

  .vital-val {
    font-size: 1.25rem;
    font-weight: 800;
  }

  .hp-bar-outer {
    height: 10px;
    background: var(--rf-bg-surface, #ffffff);
    border: 1px solid var(--rf-border-color, #121212);
    margin-top: 4px;
    overflow: hidden;
  }

  .hp-bar-inner {
    height: 100%;
    background: var(--rf-accent-secondary, #1d3557);
    transition: width 0.3s ease;
  }

  .hp-bar-inner.low {
    background: var(--rf-accent-primary, #e63946);
  }

  /* Two Column Main Content */
  .columns-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 18px;
  }

  @media (max-width: 680px) {
    .columns-layout { grid-template-columns: 1fr; }
    .vitals-grid { grid-template-columns: repeat(2, 1fr); }
  }

  .section-panel {
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 14px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    box-sizing: border-box;
  }

  .section-title {
    font-size: 0.9rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 12px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--rf-border-subtle, #d1d5db);
    padding-bottom: 6px;
  }

  /* Paper Doll & Equipment */
  .paper-doll-slots {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 14px;
  }

  .equip-slot {
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    background: var(--rf-bg-inset, #f1f3f5);
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 58px;
    box-sizing: border-box;
  }

  .equip-slot.filled {
    background: var(--rf-bg-surface, #ffffff);
  }

  .slot-label {
    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
    color: var(--rf-text-muted, #4b5563);
    display: flex;
    justify-content: space-between;
  }

  .slot-content {
    font-size: 0.85rem;
    font-weight: 700;
    margin-top: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    word-break: break-word;
  }

  .unequip-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 0.85rem;
    color: var(--rf-accent-primary, #e63946);
    font-weight: bold;
    padding: 0 4px;
  }
  .unequip-btn:hover { transform: scale(1.2); }

  /* Encumbrance Bar */
  .encumbrance-box {
    margin-top: 14px;
    padding-top: 10px;
    border-top: 1px solid var(--rf-border-subtle, #d1d5db);
  }

  .encumbrance-header {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .encumbrance-bar-bg {
    height: 12px;
    background: var(--rf-bg-inset, #f1f3f5);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    overflow: hidden;
  }

  .encumbrance-bar-fill {
    height: 100%;
    transition: width 0.3s ease, background-color 0.3s ease;
  }
  .encumbrance-bar-fill.tier-light { background: var(--rf-accent-secondary, #1d3557); }
  .encumbrance-bar-fill.tier-medium { background: #2a9d8f; }
  .encumbrance-bar-fill.tier-heavy { background: var(--rf-accent-tertiary, #ffb703); }
  .encumbrance-bar-fill.tier-overburdened { background: var(--rf-accent-primary, #e63946); }

  /* Inventory Table */
  .inventory-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
    margin-top: 8px;
  }

  .inventory-table th {
    text-align: left;
    font-size: 0.7rem;
    text-transform: uppercase;
    color: var(--rf-text-muted, #4b5563);
    padding: 4px 6px;
    border-bottom: 2px solid var(--rf-border-color, #121212);
  }

  .inventory-table td {
    padding: 6px;
    border-bottom: 1px solid var(--rf-border-subtle, #d1d5db);
    vertical-align: middle;
  }

  .inventory-row:hover { background: var(--rf-bg-inset, #f1f3f5); }

  .action-btn {
    background: var(--rf-bg-canvas, #f8f9fa);
    border: 1px solid var(--rf-border-color, #121212);
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 6px;
    cursor: pointer;
    box-shadow: 1px 1px 0px #121212;
  }
  .action-btn:hover { filter: brightness(0.9); }

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
`;
