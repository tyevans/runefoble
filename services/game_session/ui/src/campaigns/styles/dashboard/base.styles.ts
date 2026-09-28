import { css } from 'lit';

export const baseStyles = css`
  :host {
    display: block; width: 100%; box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  * { box-sizing: border-box; }

  .dashboard-header {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 16px; margin-bottom: 24px;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding-bottom: 16px;
  }

  .header-titles { display: flex; flex-direction: column; gap: 4px; }

  .dashboard-title {
    font-size: 1.75rem; font-weight: 900; letter-spacing: -0.02em;
    margin: 0; color: var(--rf-text-primary, rgb(18, 18, 18));
    text-transform: uppercase;
  }

  .dashboard-subtitle {
    font-size: 0.9rem; font-weight: 600;
    color: var(--rf-text-muted, rgb(100, 116, 139)); margin: 0;
  }

  .controls-bar {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 12px; margin-bottom: 24px;
  }

  .filter-group { display: flex; gap: 6px; flex-wrap: wrap; }

  .filter-chip {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    font-weight: 800; font-size: 0.85rem; padding: 6px 14px;
    cursor: pointer; color: var(--rf-text-primary, rgb(18, 18, 18));
    text-transform: uppercase; letter-spacing: 0.03em;
    transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.1s ease;
  }
  .filter-chip:hover {
    transform: translate(-1px, -1px);
    box-shadow: 3px 3px 0px var(--rf-shadow-color, rgb(18, 18, 18));
  }
  .filter-chip.active {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
  }

  .search-wrapper { position: relative; display: flex; align-items: center; }

  .search-input {
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-inset, rgb(248, 249, 250));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    padding: 8px 12px; font-size: 0.88rem; font-weight: 600; width: 260px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    outline: none;
  }
  .search-input:focus { border-color: var(--rf-border-focus, rgb(255, 183, 3)); }

  .btn-create-campaign {
    display: inline-flex; align-items: center; gap: 8px;
    background: var(--rf-accent-secondary, rgb(29, 53, 87));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 8px 16px; font-weight: 900; font-size: 0.9rem;
    cursor: pointer; text-transform: uppercase; letter-spacing: 0.04em;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .btn-create-campaign:hover {
    transform: translate(-2px, -2px);
    box-shadow: 4px 4px 0px var(--rf-shadow-color, rgb(18, 18, 18));
  }

  .campaigns-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 24px;
  }

  .empty-state {
    grid-column: 1 / -1;
    border: var(--rf-border-width, 2px) dashed var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    padding: 48px 24px; text-align: center;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
  }
  .empty-icon { font-size: 2.5rem; margin-bottom: 12px; }
  .empty-title { font-size: 1.25rem; font-weight: 900; margin: 0 0 8px 0; text-transform: uppercase; }
  .empty-desc { color: var(--rf-text-muted, rgb(100, 116, 139)); font-size: 0.95rem; margin: 0 0 20px 0; }
`;
