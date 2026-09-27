import { css } from 'lit';

export const layoutStyles = css`
  :host {
    display: block; box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #0f172a); background: var(--rf-surface, #f8fafc);
    border: var(--rf-border-width, 3px) solid var(--rf-border-color, #0f172a);
    box-shadow: var(--rf-shadow-hard, 5px 5px 0px #0f172a);
    max-width: 980px; margin: 0 auto; padding: 24px; position: relative;
  }
  * { box-sizing: border-box; }

  .header-banner {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 2px solid var(--rf-border-color, #0f172a); padding-bottom: 14px;
    margin-bottom: 16px; flex-wrap: wrap; gap: 12px;
  }
  .title-group h2 { margin: 0; font-size: 1.4rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; }
  .title-group p { margin: 4px 0 0 0; color: var(--rf-text-muted, #64748b); font-size: 0.85rem; }

  .role-badge {
    padding: 6px 12px; background: #ffffff; border: 2px solid #0f172a;
    box-shadow: 2px 2px 0px #0f172a; font-size: 0.8rem; text-transform: uppercase; font-weight: 700;
  }

  .notification-banner {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 16px; border: 2px solid #0f172a; box-shadow: 3px 3px 0px #0f172a;
    margin-bottom: 16px; font-size: 0.85rem; font-weight: 700;
  }
  .notification-success { background: #bbf7d0; color: #14532d; }
  .notification-warning { background: #fef08a; color: #713f12; }
  .notification-danger { background: #fecaca; color: #7f1d1d; }
  .notification-info { background: #bfdbfe; color: #1e3a8a; }

  .notification-dismiss {
    background: transparent; border: none; cursor: pointer; font-weight: 800;
    font-size: 1.1rem; line-height: 1; color: inherit; margin-left: 12px;
  }

  .filters-toolbar {
    display: flex; gap: 12px; flex-wrap: wrap; align-items: center; background: #e2e8f0;
    border: 2px solid #0f172a; padding: 10px 14px; margin-bottom: 20px; box-shadow: 2px 2px 0px #0f172a;
  }
  .filter-item { display: flex; align-items: center; gap: 6px; font-size: 0.85rem; font-weight: 700; }
  .filter-select, .search-input {
    padding: 4px 8px; border: 2px solid #0f172a; background: #ffffff; font-weight: 600; font-size: 0.85rem;
  }

  .contract-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
    gap: 16px; margin-bottom: 24px;
  }
  .empty-notice { color: #64748b; font-style: italic; }
`;
