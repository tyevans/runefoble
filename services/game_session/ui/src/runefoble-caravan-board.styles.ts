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
    max-width: 980px;
    margin: 0 auto;
    padding: 24px;
    position: relative;
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
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
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

  .role-badge {
    padding: 6px 12px;
    background: #ffffff;
    border: 2px solid #0f172a;
    box-shadow: 2px 2px 0px #0f172a;
    font-size: 0.8rem;
    text-transform: uppercase;
    font-weight: 700;
  }

  /* Real-time Status Notification Banner */
  .notification-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    border: 2px solid #0f172a;
    box-shadow: 3px 3px 0px #0f172a;
    margin-bottom: 16px;
    font-size: 0.85rem;
    font-weight: 700;
  }
  .notification-success { background: #bbf7d0; color: #14532d; }
  .notification-warning { background: #fef08a; color: #713f12; }
  .notification-danger { background: #fecaca; color: #7f1d1d; }
  .notification-info { background: #bfdbfe; color: #1e3a8a; }

  .notification-dismiss {
    background: transparent;
    border: none;
    cursor: pointer;
    font-weight: 800;
    font-size: 1.1rem;
    line-height: 1;
    color: inherit;
    margin-left: 12px;
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
    grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
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
  .risk-low { background: #86efac; color: #064e3b; }
  .risk-medium { background: #fde047; color: #713f12; }
  .risk-high { background: #fdba74; color: #7c2d12; }
  .risk-deadly { background: #fca5a5; color: #7f1d1d; }

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

  .stat-label { color: #64748b; }
  .stat-value { font-weight: 700; }
  .gold-tag { color: #b45309; font-weight: 800; }
  .rep-tag { color: #4338ca; font-weight: 800; }

  /* Active Transit Route Status Pill & Progress */
  .transit-status-pill {
    background: #f1f5f9;
    border: 1.5px solid #0f172a;
    padding: 8px 10px;
    margin: 8px 0;
    box-shadow: 1px 1px 0px #0f172a;
  }

  .transit-progress-header {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    margin-bottom: 4px;
    color: #1e293b;
  }

  .progress-track {
    height: 10px;
    background: #e2e8f0;
    border: 1.5px solid #0f172a;
    position: relative;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: #2563eb;
    transition: width 0.3s ease;
  }

  .ambush-alert-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #fee2e2;
    color: #991b1b;
    border: 1.5px solid #991b1b;
    padding: 3px 6px;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    margin-top: 6px;
    box-shadow: 1px 1px 0px #991b1b;
  }

  .card-footer {
    border-top: 1px solid #e2e8f0;
    padding-top: 8px;
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .status-badge {
    display: inline-block;
    padding: 3px 8px;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    border: 1px solid #0f172a;
    width: fit-content;
  }
  .status-open { background: #bfdbfe; color: #1e3a8a; }
  .status-accepted { background: #fed7aa; color: #7c2d12; }
  .status-in_transit { background: #fef08a; color: #713f12; }
  .status-fulfilled { background: #bbf7d0; color: #14532d; }
  .status-failed { background: #fca5a5; color: #7f1d1d; }

  .card-actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
  }

  /* Buttons */
  .btn {
    padding: 6px 12px;
    font-weight: 700;
    font-size: 0.8rem;
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
  .btn-primary { background: #2563eb; color: #ffffff; }
  .btn-success { background: #16a34a; color: #ffffff; }
  .btn-warning { background: #f59e0b; color: #0f172a; }
  .btn-outline { background: #ffffff; color: #0f172a; }
  .btn-sm { padding: 4px 8px; font-size: 0.75rem; }

  /* Modal Backdrop and Caravan Manifest Details Modal */
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(15, 23, 42, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 16px;
  }

  .manifest-modal {
    background: #ffffff;
    border: 3px solid #0f172a;
    box-shadow: 8px 8px 0px #0f172a;
    max-width: 620px;
    width: 100%;
    max-height: 85vh;
    overflow-y: auto;
    padding: 20px;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 2px solid #0f172a;
    padding-bottom: 10px;
    margin-bottom: 14px;
  }
  .modal-header h3 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 800;
    text-transform: uppercase;
  }

  .close-btn {
    background: #ffffff;
    border: 2px solid #0f172a;
    box-shadow: 2px 2px 0px #0f172a;
    font-size: 1.1rem;
    font-weight: 800;
    cursor: pointer;
    line-height: 1;
    padding: 2px 8px;
  }

  .modal-section { margin-bottom: 14px; }
  .modal-section-title {
    font-size: 0.8rem;
    font-weight: 800;
    text-transform: uppercase;
    color: #475569;
    margin-bottom: 6px;
    letter-spacing: 0.05em;
  }

  .route-summary-box {
    background: #f8fafc;
    border: 1.5px solid #0f172a;
    padding: 10px 14px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    font-size: 0.85rem;
  }

  .cargo-list { display: flex; flex-wrap: wrap; gap: 8px; }
  .cargo-pill {
    background: #ffffff;
    border: 1.5px solid #0f172a;
    box-shadow: 1px 1px 0px #0f172a;
    padding: 4px 10px;
    font-size: 0.8rem;
    font-weight: 700;
  }

  .ambush-log {
    background: #fef2f2;
    border: 1.5px solid #ef4444;
    padding: 10px 12px;
    font-size: 0.8rem;
    color: #7f1d1d;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .ambush-log-entry {
    border-bottom: 1px dashed #fca5a5;
    padding-bottom: 4px;
  }
  .ambush-log-entry:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    border-top: 2px solid #0f172a;
    padding-top: 14px;
    margin-top: 16px;
    flex-wrap: wrap;
  }
`;
