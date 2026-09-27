import { css } from 'lit';

export const characterRosterStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, rgb(18, 18, 18));
    box-sizing: border-box;
  }

  .roster-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .roster-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding-bottom: 16px;
    flex-wrap: wrap;
    gap: 16px;
  }

  .title-group h1 {
    font-size: 1.8rem;
    font-weight: 900;
    margin: 0 0 4px 0;
    text-transform: uppercase;
    letter-spacing: -0.5px;
  }

  .title-group p {
    font-size: 0.9rem;
    color: var(--rf-text-muted, rgb(75, 85, 99));
    margin: 0;
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
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .btn:hover {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow, 4px 4px 0px rgb(18, 18, 18));
  }
  .btn:active {
    transform: translate(1px, 1px);
    box-shadow: none;
  }

  .btn-primary {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: rgb(255, 255, 255);
  }

  .btn-secondary {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .btn-danger {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: rgb(255, 255, 255);
  }

  .controls-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }

  .search-input {
    flex: 1;
    min-width: 200px;
    max-width: 380px;
    padding: 8px 12px;
    font-size: 0.85rem;
    font-weight: 600;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
    box-sizing: border-box;
  }
  .search-input:focus {
    outline: none;
    border-color: var(--rf-accent-secondary, rgb(29, 53, 87));
  }

  .filter-pills {
    display: flex;
    gap: 6px;
  }

  .filter-pill {
    padding: 6px 12px;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
    cursor: pointer;
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }
  .filter-pill.active {
    background: var(--rf-accent-secondary, rgb(29, 53, 87));
    color: rgb(255, 255, 255);
  }

  .character-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 20px;
  }

  .character-card {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 4px 4px 0px rgb(18, 18, 18));
    display: flex;
    flex-direction: column;
    padding: 16px;
    gap: 12px;
    box-sizing: border-box;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .character-card:hover {
    transform: translate(-2px, -2px);
    box-shadow: 6px 6px 0px rgb(18, 18, 18);
  }

  .card-top {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .avatar-thumb {
    width: 52px;
    height: 52px;
    border: 2px solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
    background: var(--rf-bg-canvas, rgb(248, 249, 250));
    object-fit: cover;
    flex-shrink: 0;
  }

  .card-identity {
    flex: 1;
    min-width: 0;
  }

  .card-name {
    font-size: 1.1rem;
    font-weight: 900;
    margin: 0 0 2px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .card-class {
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--rf-text-muted, rgb(75, 85, 99));
  }

  .card-level-badge {
    background: var(--rf-accent-tertiary, rgb(233, 196, 106));
    color: rgb(18, 18, 18);
    border: 1px solid var(--rf-border-color, rgb(18, 18, 18));
    font-size: 0.7rem;
    font-weight: 900;
    padding: 2px 6px;
    text-transform: uppercase;
  }

  .vitals-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .hp-header {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    font-weight: 800;
  }

  .hp-bar-bg {
    height: 8px;
    background: var(--rf-bg-canvas, rgb(248, 249, 250));
    border: 1px solid var(--rf-border-color, rgb(18, 18, 18));
    overflow: hidden;
  }

  .hp-bar-fill {
    height: 100%;
    background: var(--rf-accent-secondary, rgb(42, 157, 143));
    transition: width 0.3s ease;
  }
  .hp-bar-fill.low {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
  }

  .stats-row {
    display: flex;
    gap: 8px;
  }

  .stat-chip {
    font-size: 0.75rem;
    font-weight: 800;
    background: var(--rf-bg-canvas, rgb(248, 249, 250));
    border: 1px solid var(--rf-border-color, rgb(18, 18, 18));
    padding: 3px 8px;
  }

  .campaign-badge {
    font-size: 0.75rem;
    font-weight: 800;
    padding: 4px 8px;
    border: 1px solid var(--rf-border-color, rgb(18, 18, 18));
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .campaign-badge.linked {
    background: rgb(230, 244, 234);
    color: rgb(19, 115, 51);
    border-color: rgb(19, 115, 51);
  }
  .campaign-badge.unassigned {
    background: var(--rf-bg-canvas, rgb(248, 249, 250));
    color: var(--rf-text-muted, rgb(75, 85, 99));
  }

  .card-actions {
    display: flex;
    gap: 6px;
    margin-top: auto;
    border-top: 1px solid var(--rf-border-color, rgb(18, 18, 18));
    padding-top: 10px;
    flex-wrap: wrap;
  }

  .card-actions .btn {
    flex: 1;
    font-size: 0.72rem;
    padding: 6px 8px;
    justify-content: center;
    min-width: 80px;
  }

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
