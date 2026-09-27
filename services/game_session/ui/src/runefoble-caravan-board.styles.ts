import { css } from 'lit';

export const caravanBoardStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #0f172a);
    background: var(--rf-surface, #f8fafc);
    border: var(--rf-border-width, 3px) solid var(--rf-border-color, #0f172a);
    box-shadow: var(--rf-shadow-hard, 5px 5px 0px #0f172a);
    max-width: 950px;
    margin: 0 auto;
    padding: 24px;
  }

  * {
    box-sizing: border-box;
  }

  .header-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid var(--rf-border-color, #0f172a);
    padding-bottom: 14px;
    margin-bottom: 18px;
  }

  .title-group h2 {
    margin: 0;
    font-size: 1.4rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .title-group p {
    margin: 4px 0 0 0;
    color: var(--rf-text-muted, #64748b);
    font-size: 0.85rem;
  }

  .filters-toolbar {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
    background: #e2e8f0;
    border: 2px solid #0f172a;
    padding: 10px 14px;
    margin-bottom: 20px;
    box-shadow: 2px 2px 0px #0f172a;
  }

  .filter-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85rem;
    font-weight: 700;
  }

  .filter-select {
    padding: 4px 8px;
    border: 2px solid #0f172a;
    background: #ffffff;
    font-weight: 600;
    font-size: 0.85rem;
  }

  .contract-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }

  .contract-card {
    background: #ffffff;
    border: 2px solid #0f172a;
    box-shadow: 3px 3px 0px #0f172a;
    padding: 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    cursor: pointer;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }

  .contract-card:hover {
    transform: translate(-2px, -2px);
    box-shadow: 5px 5px 0px #0f172a;
  }

  .contract-card.selected {
    border: 3px solid #2563eb;
    background: #eff6ff;
  }

  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
  }

  .route-title {
    font-size: 1rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0;
  }

  .risk-badge {
    padding: 3px 8px;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    border: 1.5px solid #0f172a;
    box-shadow: 1px 1px 0px #0f172a;
  }

  .risk-low {
    background: #86efac;
    color: #064e3b;
  }

  .risk-medium {
    background: #fde047;
    color: #713f12;
  }

  .risk-high {
    background: #fdba74;
    color: #7c2d12;
  }

  .risk-deadly {
    background: #fca5a5;
    color: #7f1d1d;
  }

  .card-stats {
    font-size: 0.85rem;
    margin: 8px 0;
    line-height: 1.4;
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .stat-label {
    color: #64748b;
  }

  .stat-value {
    font-weight: 700;
  }

  .gold-tag {
    color: #b45309;
    font-weight: 800;
  }

  .rep-tag {
    color: #4338ca;
    font-weight: 800;
  }

  .manifest-drawer {
    background: #f1f5f9;
    border: 2px solid #0f172a;
    box-shadow: 3px 3px 0px #0f172a;
    padding: 18px;
    margin-top: 16px;
  }

  .drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #cbd5e1;
    padding-bottom: 8px;
    margin-bottom: 12px;
  }

  .cargo-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 14px;
  }

  .cargo-pill {
    background: #ffffff;
    border: 1.5px solid #0f172a;
    padding: 4px 10px;
    font-size: 0.8rem;
    font-weight: 700;
  }

  .action-buttons {
    display: flex;
    gap: 10px;
    margin-top: 14px;
  }

  .btn {
    padding: 8px 16px;
    font-weight: 700;
    font-size: 0.85rem;
    text-transform: uppercase;
    cursor: pointer;
    border: 2px solid #0f172a;
    box-shadow: 2px 2px 0px #0f172a;
    transition: all 0.1s ease;
  }

  .btn:active {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px #0f172a;
  }

  .btn-primary {
    background: #3b82f6;
    color: #ffffff;
  }

  .btn-success {
    background: #22c55e;
    color: #ffffff;
  }

  .btn-warning {
    background: #f59e0b;
    color: #0f172a;
  }

  .status-badge {
    display: inline-block;
    padding: 3px 8px;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    border: 1px solid #0f172a;
    margin-top: 8px;
  }

  .status-open {
    background: #bfdbfe;
    color: #1e3a8a;
  }

  .status-accepted {
    background: #fed7aa;
    color: #7c2d12;
  }

  .status-in_transit {
    background: #fef08a;
    color: #713f12;
  }

  .status-fulfilled {
    background: #bbf7d0;
    color: #14532d;
  }
`;
