import { css } from 'lit';

export const absenteeDirectiveStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-surface);
    color: var(--rf-text-primary);
    border: 2px solid var(--rf-border-color);
    padding: 16px;
    box-sizing: border-box;
    max-width: 480px;
    margin: 0 auto;
  }
  .header {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 2px solid var(--rf-border-color);
    padding-bottom: 12px; margin-bottom: 12px;
  }
  .title-group { display: flex; flex-direction: column; gap: 2px; }
  .title { font-size: 1.05rem; font-weight: 700; margin: 0; text-transform: uppercase; letter-spacing: 0.04em; }
  .char-info { font-size: 0.8rem; color: var(--rf-text-secondary); }
  .status-pill {
    font-family: var(--rf-font-mono, monospace); font-size: 0.7rem; font-weight: 700;
    padding: 3px 8px; border-radius: 999px; text-transform: uppercase;
    background: var(--rf-status-success-bg); color: var(--rf-text-primary); border: 1px solid var(--rf-status-success);
  }
  .status-pill.offline { background: var(--rf-status-danger-bg); color: var(--rf-text-primary); border-color: var(--rf-status-danger); }
  .penalties-bar { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
  .penalty-tag {
    font-family: var(--rf-font-mono, monospace); font-size: 0.72rem;
    background: var(--rf-status-warning-bg); color: var(--rf-text-primary); border: 1px solid var(--rf-status-warning);
    padding: 2px 8px; border-radius: 4px;
  }
  .section-label {
    font-family: var(--rf-font-mono, monospace); font-size: 0.75rem;
    font-weight: 700; text-transform: uppercase; color: var(--rf-text-secondary);
    margin: 12px 0 8px; letter-spacing: 0.05em;
  }
  .stance-carousel {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 14px;
  }
  .stance-btn {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    min-height: 60px; min-width: 44px; padding: 8px 6px;
    background: var(--rf-bg-surface-elevated);
    border: 2px solid var(--rf-border-color);
    color: var(--rf-text-secondary);
    cursor: pointer; transition: all 0.15s ease;
    border-radius: 6px; text-align: center;
  }
  .stance-btn:hover { border-color: var(--rf-text-primary); color: var(--rf-text-primary); }
  .stance-btn.active {
    border-color: var(--rf-accent-secondary);
    background: color-mix(in srgb, var(--rf-accent-secondary) 15%, transparent);
    color: var(--rf-text-primary);
    box-shadow: 0 0 8px color-mix(in srgb, var(--rf-accent-secondary) 30%, transparent);
  }
  .stance-icon { font-size: 1.25rem; margin-bottom: 3px; }
  .stance-name { font-weight: 700; font-size: 0.78rem; text-transform: uppercase; }
  .stance-desc { font-size: 0.65rem; color: var(--rf-text-secondary); margin-top: 2px; line-height: 1.2; }
  .vitals-bar {
    display: flex; justify-content: space-between; align-items: center;
    background: var(--rf-bg-surface-elevated); border: 1px solid var(--rf-border-color);
    padding: 6px 10px; border-radius: 4px; font-family: var(--rf-font-mono, monospace);
    font-size: 0.75rem; margin-bottom: 12px;
  }
  .vitals-hp { color: var(--rf-status-success); font-weight: 700; }
  .vitals-stance { color: var(--rf-accent-secondary); font-weight: 600; text-transform: uppercase; }
  .haptic-alert {
    font-family: var(--rf-font-mono, monospace); font-size: 0.7rem;
    color: var(--rf-accent-secondary); text-align: center; margin-top: 8px;
  }
`;
