import { css } from 'lit';

export const strongholdStyles = css`
  :host {
    display: block;
    width: 100%;
    height: 100%;
    overflow-y: auto;
  }
  .stronghold-view { padding: 20px; display: flex; flex-direction: column; gap: 16px; }
  .dashboard-banner {
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 18px; background: #1d3557; color: #ffffff;
    border: 2px solid #121212; box-shadow: 3px 3px 0px #121212;
  }
  .banner-text h3 { margin: 0 0 4px 0; font-size: 1.15rem; }
  .banner-meta { font-size: 0.8rem; opacity: 0.9; }
  .treasury-bar {
    display: flex; gap: 10px; flex-wrap: wrap; background: #fafafa;
    border: 2px solid #121212; box-shadow: 2px 2px 0px #121212;
    padding: 10px 14px; font-size: 0.78rem; font-weight: 700;
  }
  .treasury-item { display: flex; align-items: center; gap: 4px; }
  .facility-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 14px;
  }
  .facility-card {
    background: #ffffff; border: 2px solid #121212; box-shadow: 3px 3px 0px #121212;
    padding: 14px; display: flex; flex-direction: column; gap: 8px;
  }
  .facility-header { display: flex; justify-content: space-between; align-items: center; }
  .facility-title { font-size: 0.95rem; font-weight: 800; }
  .facility-tier-badge {
    font-size: 0.7rem; font-weight: 800; padding: 2px 8px; border: 1px solid #121212; background: #ffb703;
  }
  .boons-list { margin: 4px 0; padding-left: 18px; font-size: 0.78rem; color: #2b2b2b; }
  .upgrade-btn {
    align-self: flex-start; margin-top: 4px; padding: 6px 12px; font-size: 0.75rem;
    font-weight: 800; border: 1px solid #121212; background: #2a9d8f; color: #ffffff;
    cursor: pointer; box-shadow: 1px 1px 0px #121212;
  }
  .upgrade-btn:hover { transform: translate(-1px, -1px); box-shadow: 2px 2px 0px #121212; }
`;
