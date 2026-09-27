import { css } from 'lit';

export const absenteeDirectiveStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-surface, #121316);
    color: var(--rf-text-primary, #f5f7fa);
    border: 2px solid var(--rf-border-color, #3b3e47);
    padding: 16px;
    box-sizing: border-box;
    max-width: 480px;
    margin: 0 auto;
  }
  .header {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 2px solid var(--rf-border-color, #3b3e47);
    padding-bottom: 12px; margin-bottom: 12px;
  }
  .title-group { display: flex; flex-direction: column; gap: 2px; }
  .title { font-size: 1.05rem; font-weight: 700; margin: 0; text-transform: uppercase; letter-spacing: 0.04em; }
  .char-info { font-size: 0.8rem; color: var(--rf-text-secondary, #a0a5b2); }
  .status-pill {
    font-family: var(--rf-font-mono, monospace); font-size: 0.7rem; font-weight: 700;
    padding: 3px 8px; border-radius: 999px; text-transform: uppercase;
    background: #064e3b; color: #6ee7b7; border: 1px solid #10b981;
  }
  .status-pill.offline { background: #450a0a; color: #fca5a5; border-color: #ef4444; }
  .penalties-bar { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
  .penalty-tag {
    font-family: var(--rf-font-mono, monospace); font-size: 0.72rem;
    background: #451a03; color: #fdba74; border: 1px solid #f97316;
    padding: 2px 8px; border-radius: 4px;
  }
  .section-label {
    font-family: var(--rf-font-mono, monospace); font-size: 0.75rem;
    font-weight: 700; text-transform: uppercase; color: var(--rf-text-secondary, #a0a5b2);
    margin: 12px 0 8px; letter-spacing: 0.05em;
  }
  .stance-carousel {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 14px;
  }
  .stance-btn {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    min-height: 60px; min-width: 44px; padding: 8px 6px;
    background: var(--rf-bg-surface-raised, #1a1b1f);
    border: 2px solid var(--rf-border-color, #3b3e47);
    color: var(--rf-text-secondary, #a0a5b2);
    cursor: pointer; transition: all 0.15s ease;
    border-radius: 6px; text-align: center;
  }
  .stance-btn:hover { border-color: var(--rf-text-primary, #f5f7fa); color: var(--rf-text-primary, #f5f7fa); }
  .stance-btn.active {
    border-color: var(--rf-color-accent, #3b82f6);
    background: rgba(59, 130, 246, 0.15);
    color: var(--rf-text-primary, #f5f7fa);
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.3);
  }
  .stance-icon { font-size: 1.25rem; margin-bottom: 3px; }
  .stance-name { font-weight: 700; font-size: 0.78rem; text-transform: uppercase; }
  .stance-desc { font-size: 0.65rem; color: var(--rf-text-secondary, #a0a5b2); margin-top: 2px; line-height: 1.2; }
  .vitals-bar {
    display: flex; justify-content: space-between; align-items: center;
    background: var(--rf-bg-surface-raised, #1a1b1f); border: 1px solid var(--rf-border-color, #3b3e47);
    padding: 6px 10px; border-radius: 4px; font-family: var(--rf-font-mono, monospace);
    font-size: 0.75rem; margin-bottom: 12px;
  }
  .vitals-hp { color: #10b981; font-weight: 700; }
  .vitals-stance { color: var(--rf-color-accent, #3b82f6); font-weight: 600; text-transform: uppercase; }
  .haptic-alert {
    font-family: var(--rf-font-mono, monospace); font-size: 0.7rem;
    color: var(--rf-color-accent, #3b82f6); text-align: center; margin-top: 8px;
  }
`;
