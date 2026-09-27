import { css } from 'lit';

export const vocalModulatorStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #18181b);
  }
  .modulator-panel {
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #18181b);
    box-shadow: var(--rf-shadow, 4px 4px 0px #18181b);
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    box-sizing: border-box;
  }
  .header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .indicator-group { display: flex; align-items: center; gap: 8px; }
  .led-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid var(--rf-border-color, #18181b);
    background: var(--rf-text-muted, #71717a);
    transition: all 0.2s ease;
  }
  .led-indicator.active {
    background: var(--rf-accent-primary, #e11d48);
    box-shadow: 0 0 8px var(--rf-accent-primary, #e11d48);
    animation: led-pulse 1.6s infinite ease-in-out;
  }
  @keyframes led-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(0.92); }
  }
  .title { font-weight: 800; font-size: 0.95rem; letter-spacing: 0.5px; text-transform: uppercase; }
  .badge-active {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 6px;
    border: 1px solid var(--rf-border-color, #18181b);
    background: var(--rf-accent-tertiary, #fde047);
  }
  .bypass-btn {
    padding: 4px 10px;
    font-size: 0.75rem;
    font-weight: 700;
    cursor: pointer;
    background: var(--rf-bg-canvas, #f4f4f5);
    border: 2px solid var(--rf-border-color, #18181b);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #18181b);
  }
  .bypass-btn.active { background: var(--rf-accent-primary, #e11d48); color: var(--rf-text-inverse, #ffffff); }
  .preset-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .preset-card {
    background: var(--rf-bg-surface, #ffffff);
    border: 2px solid var(--rf-border-color, #18181b);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #18181b);
    padding: 8px 6px;
    text-align: center;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    transition: transform 0.1s ease;
  }
  .preset-card:hover { transform: translate(-1px, -1px); box-shadow: var(--rf-shadow, 4px 4px 0px #18181b); }
  .preset-card.selected { background: var(--rf-accent-tertiary, #fde047); font-weight: 700; }
  .preset-icon { font-size: 1.25rem; line-height: 1; }
  .preset-name { font-size: 0.72rem; font-weight: 700; }
  .key-badge {
    font-size: 0.6rem;
    padding: 1px 4px;
    border: 1px solid var(--rf-border-color, #18181b);
    background: var(--rf-bg-canvas, #f4f4f5);
    font-family: monospace;
  }
  .toggle-sliders-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 0.72rem;
    font-weight: 600;
    text-decoration: underline;
    color: var(--rf-text-muted, #71717a);
    text-align: right;
    padding: 2px 0;
  }
`;
