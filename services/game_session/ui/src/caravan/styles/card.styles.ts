import { css } from 'lit';

export const cardStyles = css`
  * { box-sizing: border-box; }

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
  .contract-card:hover { transform: translate(-2px, -2px); box-shadow: 5px 5px 0px #0f172a; }
  .contract-card.selected { border: 3px solid #2563eb; background: #eff6ff; }

  .card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
  .route-title { font-size: 1rem; font-weight: 800; color: #0f172a; margin: 0; }

  .risk-badge {
    padding: 3px 8px; font-size: 0.72rem; font-weight: 800; text-transform: uppercase;
    border: 1.5px solid #0f172a; box-shadow: 1px 1px 0px #0f172a;
  }
  .risk-low { background: #86efac; color: #064e3b; }
  .risk-medium { background: #fde047; color: #713f12; }
  .risk-high { background: #fdba74; color: #7c2d12; }
  .risk-deadly { background: #fca5a5; color: #7f1d1d; }

  .card-stats { font-size: 0.85rem; margin: 8px 0; line-height: 1.4; }
  .stat-row { display: flex; justify-content: space-between; margin-bottom: 4px; }
  .stat-label { color: #64748b; }
  .stat-value { font-weight: 700; }
  .gold-tag { color: #b45309; font-weight: 800; }
  .rep-tag { color: #4338ca; font-weight: 800; }

  .transit-status-pill {
    background: #f1f5f9; border: 1.5px solid #0f172a; padding: 8px 10px; margin: 8px 0; box-shadow: 1px 1px 0px #0f172a;
  }
  .transit-progress-header {
    display: flex; justify-content: space-between; font-size: 0.75rem; font-weight: 800;
    text-transform: uppercase; margin-bottom: 4px; color: #1e293b;
  }
  .progress-track { height: 10px; background: #e2e8f0; border: 1.5px solid #0f172a; position: relative; overflow: hidden; }
  .progress-fill { height: 100%; background: #2563eb; transition: width 0.3s ease; }

  .ambush-alert-badge {
    display: inline-flex; align-items: center; gap: 4px; background: #fee2e2; color: #991b1b;
    border: 1.5px solid #991b1b; padding: 3px 6px; font-size: 0.72rem; font-weight: 800;
    text-transform: uppercase; margin-top: 6px; box-shadow: 1px 1px 0px #991b1b;
  }

  .card-footer {
    border-top: 1px solid #e2e8f0; padding-top: 8px; margin-top: 8px;
    display: flex; flex-direction: column; gap: 8px;
  }
  .status-badge {
    display: inline-block; padding: 3px 8px; font-size: 0.72rem; font-weight: 800;
    text-transform: uppercase; border: 1px solid #0f172a; width: fit-content;
  }
  .status-open { background: #bfdbfe; color: #1e3a8a; }
  .status-accepted { background: #fed7aa; color: #7c2d12; }
  .status-in_transit { background: #fef08a; color: #713f12; }
  .status-fulfilled { background: #bbf7d0; color: #14532d; }
  .status-failed { background: #fca5a5; color: #7f1d1d; }

  .card-actions { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .btn {
    padding: 6px 12px; font-weight: 700; font-size: 0.8rem; text-transform: uppercase;
    cursor: pointer; border: 2px solid #0f172a; box-shadow: 2px 2px 0px #0f172a; transition: all 0.1s ease;
  }
  .btn:active { transform: translate(1px, 1px); box-shadow: 1px 1px 0px #0f172a; }
  .btn-primary { background: #2563eb; color: #ffffff; }
  .btn-success { background: #16a34a; color: #ffffff; }
  .btn-warning { background: #f59e0b; color: #0f172a; }
  .btn-outline { background: #ffffff; color: #0f172a; }
  .btn-sm { padding: 4px 8px; font-size: 0.75rem; }
`;
