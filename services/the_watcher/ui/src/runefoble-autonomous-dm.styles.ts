import { css } from 'lit';

export const autonomousDmStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary);
    background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    box-shadow: var(--rf-shadow);
    padding: 20px;
    box-sizing: border-box;
    max-width: 640px;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
    padding-bottom: 12px;
    margin-bottom: 16px;
  }

  .title-group {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .title-group h3 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 900;
    letter-spacing: -0.02em;
    text-transform: uppercase;
  }

  .badge {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    padding: 3px 8px;
    border: 1px solid var(--rf-border-color);
    letter-spacing: 0.05em;
  }

  .badge-lighting {
    background: var(--rf-accent-tertiary);
    color: var(--rf-text-primary);
  }

  .badge-threat {
    background: var(--rf-accent-primary);
    color: var(--rf-text-inverse);
  }

  .badge-threat.easy {
    background: var(--rf-success, var(--rf-accent-secondary));
    color: var(--rf-text-inverse);
  }

  .badge-threat.medium {
    background: var(--rf-warning, var(--rf-accent-tertiary));
    color: var(--rf-text-primary);
  }

  .badge-threat.hard {
    background: var(--rf-accent-primary);
    color: var(--rf-text-inverse);
  }

  .badge-threat.deadly {
    background: var(--rf-accent-primary);
    color: var(--rf-text-inverse);
  }

  .scene-box {
    background: var(--rf-bg-canvas);
    border: 1px solid var(--rf-border-color);
    padding: 12px;
    margin-bottom: 14px;
  }

  .scene-title {
    font-weight: 800;
    font-size: 1rem;
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .scene-desc {
    font-size: 0.88rem;
    line-height: 1.45;
    margin: 6px 0;
    color: var(--rf-text-primary);
  }

  .ambient-audio {
    font-size: 0.78rem;
    color: var(--rf-text-muted);
    font-style: italic;
    margin-top: 4px;
  }

  .encounter-section {
    margin-top: 14px;
  }

  .section-title {
    font-size: 0.85rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .tactical-obj {
    font-size: 0.82rem;
    padding: 6px 10px;
    background: var(--rf-bg-inset, var(--rf-bg-canvas));
    border: 1px solid var(--rf-border-subtle, var(--rf-border-color));
    color: var(--rf-text-secondary, var(--rf-text-primary));
    font-weight: 600;
    margin-bottom: 10px;
  }

  .monsters-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 14px;
  }

  .monster-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 10px;
    border: 1px solid var(--rf-border-subtle, var(--rf-border-color));
    background: var(--rf-bg-surface);
    font-size: 0.82rem;
  }

  .monster-name {
    font-weight: 700;
  }

  .monster-stats {
    font-family: monospace;
    font-size: 0.78rem;
    color: var(--rf-text-muted);
  }

  .action-resolved-box {
    margin-top: 12px;
    padding: 10px;
    border: 2px solid var(--rf-accent-primary);
    background: var(--rf-bg-inset, var(--rf-bg-canvas));
    color: var(--rf-accent-primary);
    font-size: 0.82rem;
  }

  .action-resolved-title {
    font-weight: 800;
    text-transform: uppercase;
    margin-bottom: 4px;
  }

  .controls-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 8px;
    margin-top: 16px;
    padding-top: 14px;
    border-top: var(--rf-border-width, 2px) solid var(--rf-border-color);
  }

  button.rf-btn {
    font-family: inherit;
    font-size: 0.82rem;
    font-weight: 800;
    text-transform: uppercase;
    padding: 10px 8px;
    cursor: pointer;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    box-shadow: var(--rf-shadow-sm);
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }

  button.rf-btn:hover {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow);
  }

  button.rf-btn:active {
    transform: translate(1px, 1px);
    box-shadow: none;
  }

  .btn-scene {
    background: var(--rf-accent-secondary);
    color: var(--rf-text-inverse);
  }

  .btn-encounter {
    background: var(--rf-accent-tertiary);
    color: var(--rf-text-primary);
  }

  .btn-turn {
    background: var(--rf-accent-primary);
    color: var(--rf-text-inverse);
  }
`;
