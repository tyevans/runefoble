import { css } from 'lit';

export const characterSheetInventoryStyles = css`
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
`;

export const inventoryStyles = characterSheetInventoryStyles;
