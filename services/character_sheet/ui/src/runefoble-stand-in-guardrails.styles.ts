import { css } from 'lit';

export const standInGuardrailsStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-card, #1e1e24);
    border: var(--rf-border-width, 1px) solid var(--rf-border-color, #2d2d39);
    border-radius: var(--rf-border-radius, 8px);
    padding: 24px;
    color: var(--rf-text-primary, #f3f4f6);
    max-width: 580px;
    box-sizing: border-box;
    box-shadow: var(--rf-shadow, 0 4px 6px -1px rgba(0, 0, 0, 0.3));
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
    border-bottom: 1px solid var(--rf-border-subtle, #374151);
    padding-bottom: 12px;
  }
  .header h3 {
    margin: 0;
    font-size: 1.25rem;
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--rf-text-primary, #f3f4f6);
  }
  .subtext { font-size: 0.85rem; color: var(--rf-text-muted, #9ca3af); margin-top: 4px; }
  .section {
    margin-bottom: 16px;
    background: var(--rf-bg-inset, #131317);
    border: 1px solid var(--rf-border-subtle, #374151);
    border-radius: 8px;
    padding: 14px;
  }
  .section-title {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 700;
    color: var(--rf-accent-secondary, #60a5fa);
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .toggle-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  .toggle-row:last-child { border-bottom: none; }
  .toggle-label { font-size: 0.9rem; font-weight: 500; }
  .toggle-desc { font-size: 0.75rem; color: var(--rf-text-muted, #9ca3af); }
  input[type='checkbox'] {
    width: 18px; height: 18px; cursor: pointer; accent-color: var(--rf-accent-secondary, #3b82f6);
  }
  .chips-container { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
  .chip {
    background: var(--rf-accent-tertiary, #f59e0b);
    color: #111827;
    font-weight: 600;
    font-size: 0.8rem;
    padding: 3px 10px;
    border-radius: 9999px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .chip-remove { cursor: pointer; font-weight: bold; }
  .chip-priority { background: var(--rf-accent-secondary, #3b82f6); color: #ffffff; }
  .input-row { display: flex; gap: 8px; margin-top: 8px; }
  input[type='text'], select {
    flex: 1;
    background: var(--rf-bg-card, #1e1e24);
    border: 1px solid var(--rf-border-subtle, #374151);
    border-radius: 6px;
    color: var(--rf-text-primary, #f3f4f6);
    padding: 6px 10px;
    font-size: 0.85rem;
  }
  input[type='range'] { flex: 1; accent-color: var(--rf-accent-secondary, #3b82f6); cursor: pointer; }
  .slider-row { display: flex; align-items: center; gap: 12px; margin-top: 6px; }
  .slider-val { font-size: 0.85rem; font-weight: 600; min-width: 48px; color: var(--rf-accent-secondary, #60a5fa); }
  .btn {
    background: var(--rf-accent-secondary, #3b82f6);
    color: var(--rf-text-inverse, #ffffff);
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  .btn:hover { opacity: 0.9; }
  .btn-secondary {
    background: var(--rf-bg-inset, #2b2b36);
    border: 1px solid var(--rf-border-subtle, #374151);
    color: var(--rf-text-primary, #f3f4f6);
  }
  .btn-takeover { background: var(--rf-accent-primary, #10b981); }
  .actions-bar { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; }
  .status-msg { font-size: 0.8rem; color: var(--rf-accent-primary, #10b981); }
`;
