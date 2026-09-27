import { css } from 'lit';

export const settingsModalTabsStyles = css`
  .nav-tabs {
    display: flex; gap: 4px;
    padding: 8px 16px 0;
    background: var(--rf-bg-canvas);
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
    overflow-x: auto;
  }

  .tab-btn {
    padding: 8px 14px;
    font-size: 0.85rem; font-weight: 700;
    border: var(--rf-border-width, 2px) solid transparent;
    border-bottom: none;
    background: transparent;
    color: var(--rf-text-muted);
    cursor: pointer;
    display: inline-flex; align-items: center; gap: 6px;
    transition: all 0.15s ease;
  }
  .tab-btn:hover:not(.active) {
    color: var(--rf-text-primary);
    background: var(--rf-bg-surface);
  }
  .tab-btn.active {
    background: var(--rf-bg-surface);
    color: var(--rf-text-primary);
    border-color: var(--rf-border-color);
    border-bottom: 2px solid var(--rf-bg-surface);
    margin-bottom: -2px;
  }

  .section-title {
    font-size: 0.82rem; font-weight: 900;
    text-transform: uppercase; letter-spacing: 0.06em;
    margin: 0 0 12px 0;
    color: var(--rf-text-muted);
    display: flex; align-items: center; gap: 6px;
  }

  .segmented-group {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    background: var(--rf-bg-canvas);
    padding: 6px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm);
  }

  .segment-btn {
    padding: 10px 12px;
    font-size: 0.85rem; font-weight: 700;
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    cursor: pointer;
    background: var(--rf-bg-surface);
    color: var(--rf-text-primary);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    transition: all 0.12s ease;
  }
  .segment-btn:hover:not(.active) {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow-sm);
  }
  .segment-btn.active {
    background: var(--rf-accent-tertiary);
    color: var(--rf-text-primary);
    font-weight: 900;
    box-shadow: var(--rf-shadow-sm);
  }

  .theme-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 14px;
  }

  .theme-card {
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    padding: 14px;
    background: var(--rf-bg-surface);
    color: var(--rf-text-primary);
    box-shadow: var(--rf-shadow-sm);
    cursor: pointer;
    display: flex; flex-direction: column; gap: 10px;
    text-align: left;
    transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
  }
  .theme-card:hover:not(.active) {
    transform: translate(-2px, -2px);
    box-shadow: var(--rf-shadow);
  }
  .theme-card.active {
    border-color: var(--rf-border-color);
    outline: 2px solid var(--rf-accent-primary);
    outline-offset: 2px;
    box-shadow: var(--rf-shadow);
    background: var(--rf-bg-card);
  }

  .theme-card-header {
    display: flex; align-items: center; justify-content: space-between;
  }
  .theme-card-title {
    font-size: 0.95rem; font-weight: 800;
    margin: 0;
    display: flex; align-items: center; gap: 6px;
  }
  .active-tag {
    font-size: 0.7rem; font-weight: 800;
    text-transform: uppercase;
    padding: 2px 6px;
    background: var(--rf-accent-primary);
    color: var(--rf-text-inverse);
    border: 1px solid var(--rf-border-color);
  }
  .theme-desc {
    font-size: 0.8rem;
    color: var(--rf-text-muted);
    margin: 0;
    line-height: 1.35;
  }
`;

export const tabsStyles = settingsModalTabsStyles;
