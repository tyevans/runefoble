import { css } from 'lit';

export const duplexControlStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #111111);
  }
  .duplex-panel {
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #111111);
    box-shadow: var(--rf-shadow, 4px 4px 0px rgba(0, 0, 0, 0.9));
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    box-sizing: border-box;
  }
  .header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    border-bottom: 2px solid var(--rf-border-subtle, #e4e4e7);
    padding-bottom: 8px;
  }
  .title-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .duplex-title {
    font-weight: 800;
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0;
  }
  .status-badges {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .badge {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 7px;
    border: 1px solid var(--rf-border-color, #111111);
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }
  .badge-live { background: var(--rf-accent-secondary, #22c55e); color: #000; }
  .badge-dm { background: var(--rf-accent-tertiary, #eab308); color: #000; }
  .badge-muted { background: var(--rf-accent-primary, #ef4444); color: #fff; }
  .badge-idle { background: var(--rf-bg-inset, #e4e4e7); color: var(--rf-text-muted, #71717a); }
  .actions-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
  .btn {
    font-family: inherit;
    font-weight: 700;
    font-size: 0.82rem;
    padding: 8px 14px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #111111);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgba(0, 0, 0, 0.9));
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .btn:hover:not(:disabled) { transform: translate(-1px, -1px); }
  .btn:active:not(:disabled) { transform: translate(1px, 1px); box-shadow: none; }
  .btn-primary { background: var(--rf-accent-primary, #ef4444); color: var(--rf-text-inverse, #fff); }
  .btn-secondary { background: var(--rf-bg-surface, #fff); color: var(--rf-text-primary, #111); }
  .btn-warning { background: var(--rf-accent-tertiary, #eab308); color: var(--rf-text-primary, #111); }
  .btn-toggle-active { background: var(--rf-border-color, #111111); color: var(--rf-text-inverse, #fff); }
  .narration-tail {
    font-size: 0.78rem;
    font-style: italic;
    color: var(--rf-text-muted, #71717a);
    padding: 6px 10px;
    background: var(--rf-bg-canvas, #f4f4f5);
    border-left: 3px solid var(--rf-accent-primary, #ef4444);
  }
`;
