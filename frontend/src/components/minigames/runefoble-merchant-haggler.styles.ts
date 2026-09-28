import { css } from 'lit';

export const merchantHagglerStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #0f172a);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 3px) solid var(--rf-border-color, #0f172a);
    box-shadow: var(--rf-shadow-hard, 5px 5px 0px #0f172a);
    max-width: 820px;
    margin: 0 auto;
    padding: 20px;
  }

  * {
    box-sizing: border-box;
  }

  .haggler-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid var(--rf-border-color, #0f172a);
    padding-bottom: 12px;
    margin-bottom: 16px;
  }

  .merchant-profile {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .merchant-avatar {
    width: 52px;
    height: 52px;
    border: 2px solid var(--rf-border-color, #0f172a);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 1.4rem;
    background: #fbbf24;
    box-shadow: 2px 2px 0px #0f172a;
  }

  .merchant-meta h3 {
    margin: 0;
    font-size: 1.2rem;
    font-weight: 800;
    text-transform: uppercase;
  }

  .merchant-badges {
    display: flex;
    gap: 8px;
    margin-top: 4px;
  }

  .badge {
    padding: 2px 8px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    border: 1px solid #0f172a;
    border-radius: 2px;
  }

  .badge-temperament {
    background: #e0e7ff;
    color: #3730a3;
  }

  .badge-emotion {
    background: #fef3c7;
    color: #92400e;
  }

  .badge-emotion.enraged {
    background: #fee2e2;
    color: #991b1b;
  }

  .badge-emotion.pleased {
    background: #dcfce7;
    color: #166534;
  }

  .patience-container {
    text-align: right;
  }

  .patience-label {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
  }

  .patience-meter {
    display: flex;
    gap: 4px;
    justify-content: flex-end;
  }

  .patience-pip {
    width: 14px;
    height: 14px;
    border: 2px solid #0f172a;
    background: #e2e8f0;
    border-radius: 2px;
  }

  .patience-pip.filled {
    background: #10b981;
  }

  .patience-pip.warning {
    background: #f59e0b;
  }

  .patience-pip.danger {
    background: #ef4444;
  }

  /* Price Tug-of-War Section */
  .price-section {
    background: #f8fafc;
    border: 2px solid var(--rf-border-color, #0f172a);
    padding: 16px;
    margin-bottom: 16px;
    box-shadow: 2px 2px 0px #0f172a;
  }

  .price-meter-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    font-weight: 700;
    font-size: 0.9rem;
  }

  .price-tug-track {
    position: relative;
    height: 24px;
    background: #e2e8f0;
    border: 2px solid #0f172a;
    margin-bottom: 12px;
  }

  .price-tug-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #10b981);
    transition: width 0.3s ease;
  }

  .price-tags {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    font-weight: 700;
  }

  .price-tag-value {
    color: #b45309;
    font-size: 1rem;
  }

  /* Dialogue Bark Bubble */
  .bark-box {
    position: relative;
    background: #fffbeb;
    border: 2px solid #0f172a;
    padding: 14px 18px;
    margin-bottom: 16px;
    border-radius: 4px;
    font-style: italic;
    font-weight: 600;
    box-shadow: 3px 3px 0px #0f172a;
    min-height: 48px;
    display: flex;
    align-items: center;
  }

  .bark-box::after {
    content: '';
    position: absolute;
    top: -10px;
    left: 28px;
    border-width: 0 10px 10px;
    border-style: solid;
    border-color: #0f172a transparent;
    display: block;
    width: 0;
  }

  /* Gambits Grid */
  .gambits-label {
    font-size: 0.85rem;
    font-weight: 800;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  .gambits-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 8px;
    margin-bottom: 16px;
  }

  .gambit-card {
    background: #f1f5f9;
    border: 2px solid #0f172a;
    padding: 10px 8px;
    text-align: center;
    cursor: pointer;
    font-weight: 700;
    font-size: 0.8rem;
    box-shadow: 2px 2px 0px #0f172a;
    transition: transform 0.1s ease, background 0.15s ease;
    user-select: none;
  }

  .gambit-card:hover {
    background: #e2e8f0;
    transform: translate(-1px, -1px);
    box-shadow: 3px 3px 0px #0f172a;
  }

  .gambit-card.selected {
    background: #f59e0b;
    color: #ffffff;
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px #0f172a;
  }

  /* Controls Row */
  .controls-row {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .offer-input-group {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .offer-input {
    width: 90px;
    padding: 8px;
    border: 2px solid #0f172a;
    font-weight: 800;
    font-size: 1rem;
    text-align: right;
  }

  .btn {
    border: 2px solid #0f172a;
    padding: 10px 18px;
    font-weight: 800;
    font-size: 0.85rem;
    text-transform: uppercase;
    cursor: pointer;
    box-shadow: 2px 2px 0px #0f172a;
    transition: all 0.1s ease;
  }

  .btn:active {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px #0f172a;
  }

  .btn-submit {
    background: #2563eb;
    color: #ffffff;
    flex: 1;
  }

  .btn-accept {
    background: #10b981;
    color: #ffffff;
  }

  .status-banner {
    padding: 8px 12px;
    font-weight: 800;
    text-align: center;
    border: 2px solid #0f172a;
    margin-bottom: 12px;
    text-transform: uppercase;
  }

  .status-banner.completed {
    background: #dcfce7;
    color: #15803d;
  }

  .status-banner.refused,
  .status-banner.terminated {
    background: #fee2e2;
    color: #b91c1c;
  }
`;
