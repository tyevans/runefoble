import { css } from 'lit';

export const espionageStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-surface, #121316);
    color: var(--rf-text-primary, #f5f7fa);
    border: 2px solid var(--rf-border-color, #3b3e47);
    padding: 16px;
    box-sizing: border-box;
  }
  .header {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 2px solid var(--rf-border-color, #3b3e47);
    padding-bottom: 12px; margin-bottom: 16px; gap: 8px; flex-wrap: wrap;
  }
  .title-group { display: flex; align-items: center; gap: 8px; }
  .title {
    font-size: 1.1rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.05em; margin: 0;
  }
  .campaign-tag {
    font-family: var(--rf-font-mono, monospace); font-size: 0.75rem;
    background: var(--rf-bg-surface-raised, #232730); padding: 2px 6px;
    border: 1px solid var(--rf-border-color, #3b3e47);
  }
  .filters { display: flex; gap: 4px; }
  .filter-btn {
    background: transparent; border: 1px solid var(--rf-border-color, #3b3e47);
    color: var(--rf-text-secondary, #a0a5b2); font-family: var(--rf-font-mono, monospace);
    font-size: 0.7rem; font-weight: 600; padding: 4px 8px; cursor: pointer; text-transform: uppercase;
  }
  .filter-btn:hover { color: var(--rf-text-primary, #f5f7fa); border-color: var(--rf-text-primary, #f5f7fa); }
  .filter-btn.active {
    background: var(--rf-text-primary, #f5f7fa); color: var(--rf-bg-surface, #121316);
    border-color: var(--rf-text-primary, #f5f7fa);
  }
  .section-title {
    font-family: var(--rf-font-mono, monospace); font-size: 0.8rem; font-weight: 700;
    text-transform: uppercase; color: var(--rf-text-secondary, #a0a5b2); margin: 16px 0 8px; letter-spacing: 0.04em;
  }
  .regional-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 8px; margin-bottom: 16px;
  }
  .region-chip {
    border: 1px solid var(--rf-border-color, #3b3e47); background: var(--rf-bg-surface-raised, #1a1b1f);
    padding: 8px; display: flex; flex-direction: column; gap: 4px;
  }
  .region-name { font-size: 0.8rem; font-weight: 600; }
  .card-list { display: flex; flex-direction: column; gap: 8px; }
  .card {
    border: 1px solid var(--rf-border-color, #3b3e47); background: var(--rf-bg-surface-raised, #1a1b1f);
    padding: 10px 12px; cursor: pointer; transition: border-color 0.15s ease;
  }
  .card:hover, .card.selected { border-color: var(--rf-color-accent, #3b82f6); }
  .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; gap: 8px; }
  .card-title { font-size: 0.9rem; font-weight: 600; margin: 0; }
  .card-meta { font-size: 0.75rem; color: var(--rf-text-secondary, #a0a5b2); }
  .card-summary { font-size: 0.82rem; line-height: 1.4; color: var(--rf-text-secondary, #a0a5b2); margin: 4px 0 0; }
  .badge {
    font-family: var(--rf-font-mono, monospace); font-size: 0.65rem; font-weight: 700;
    padding: 2px 6px; text-transform: uppercase; letter-spacing: 0.04em; border-radius: 2px;
  }
  .badge-critical { background: #450a0a; color: #fca5a5; border: 1px solid #ef4444; }
  .badge-high { background: #451a03; color: #fdba74; border: 1px solid #f97316; }
  .badge-medium { background: #1e1b4b; color: #c7d2fe; border: 1px solid #6366f1; }
  .badge-low { background: #064e3b; color: #6ee7b7; border: 1px solid #10b981; }
  .dossier-panel {
    margin-top: 8px; padding: 8px; border-left: 3px solid var(--rf-color-accent, #3b82f6);
    background: rgba(59, 130, 246, 0.08); font-family: var(--rf-font-mono, monospace); font-size: 0.8rem;
  }
  .empty-state { font-style: italic; color: var(--rf-text-secondary, #a0a5b2); padding: 16px 0; text-align: center; }
`;
