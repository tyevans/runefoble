import { css } from 'lit';

export const espionageStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-surface);
    color: var(--rf-text-primary);
    border: 2px solid var(--rf-border-color);
    padding: 16px;
    box-sizing: border-box;
  }
  .header {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 2px solid var(--rf-border-color);
    padding-bottom: 12px; margin-bottom: 16px; gap: 8px; flex-wrap: wrap;
  }
  .title-group { display: flex; align-items: center; gap: 8px; }
  .title {
    font-size: 1.1rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.05em; margin: 0;
  }
  .campaign-tag {
    font-family: var(--rf-font-mono, monospace); font-size: 0.75rem;
    background: var(--rf-bg-surface-elevated); padding: 2px 6px;
    border: 1px solid var(--rf-border-color);
  }
  .filters { display: flex; gap: 4px; }
  .filter-btn {
    background: transparent; border: 1px solid var(--rf-border-color);
    color: var(--rf-text-secondary); font-family: var(--rf-font-mono, monospace);
    font-size: 0.7rem; font-weight: 600; padding: 4px 8px; cursor: pointer; text-transform: uppercase;
  }
  .filter-btn:hover { color: var(--rf-text-primary); border-color: var(--rf-text-primary); }
  .filter-btn.active {
    background: var(--rf-text-primary); color: var(--rf-bg-surface);
    border-color: var(--rf-text-primary);
  }
  .section-title {
    font-family: var(--rf-font-mono, monospace); font-size: 0.8rem; font-weight: 700;
    text-transform: uppercase; color: var(--rf-text-secondary); margin: 16px 0 8px; letter-spacing: 0.04em;
  }
  .regional-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 8px; margin-bottom: 16px;
  }
  .region-chip {
    border: 1px solid var(--rf-border-color); background: var(--rf-bg-surface-elevated);
    padding: 8px; display: flex; flex-direction: column; gap: 4px;
  }
  .region-name { font-size: 0.8rem; font-weight: 600; }
  .card-list { display: flex; flex-direction: column; gap: 8px; }
  .card {
    border: 1px solid var(--rf-border-color); background: var(--rf-bg-surface-elevated);
    padding: 10px 12px; cursor: pointer; transition: border-color 0.15s ease;
  }
  .card:hover, .card.selected { border-color: var(--rf-accent-secondary); }
  .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; gap: 8px; }
  .card-title { font-size: 0.9rem; font-weight: 600; margin: 0; }
  .card-meta { font-size: 0.75rem; color: var(--rf-text-secondary); }
  .card-summary { font-size: 0.82rem; line-height: 1.4; color: var(--rf-text-secondary); margin: 4px 0 0; }
  .badge {
    font-family: var(--rf-font-mono, monospace); font-size: 0.65rem; font-weight: 700;
    padding: 2px 6px; text-transform: uppercase; letter-spacing: 0.04em; border-radius: 2px;
  }
  .badge-critical { background: var(--rf-status-danger-bg); color: var(--rf-text-primary); border: 1px solid var(--rf-status-danger); }
  .badge-high { background: var(--rf-status-warning-bg); color: var(--rf-text-primary); border: 1px solid var(--rf-status-warning); }
  .badge-medium { background: var(--rf-status-info-bg); color: var(--rf-text-primary); border: 1px solid var(--rf-status-info); }
  .badge-low { background: var(--rf-status-success-bg); color: var(--rf-text-primary); border: 1px solid var(--rf-status-success); }
  .dossier-panel {
    margin-top: 8px; padding: 8px; border-left: 3px solid var(--rf-accent-secondary);
    background: color-mix(in srgb, var(--rf-accent-secondary) 8%, transparent); font-family: var(--rf-font-mono, monospace); font-size: 0.8rem;
  }
  .empty-state { font-style: italic; color: var(--rf-text-secondary); padding: 16px 0; text-align: center; }
`;
