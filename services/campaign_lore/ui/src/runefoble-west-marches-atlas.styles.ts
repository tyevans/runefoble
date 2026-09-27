import { css } from 'lit';
import { mapStyles, pinStyles, strongholdStyles } from './west_marches/styles/index.ts';

const baseAtlasStyles = css`
  :host {
    display: flex;
    flex-direction: column;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    color: var(--rf-text-primary, #121212);
    width: 1040px;
    height: 700px;
    max-width: 100%;
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
  }

  .top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: #fafafa;
    border-bottom: 2px solid #121212;
    z-index: 10;
    gap: 8px;
  }

  .title-group {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .title {
    font-size: 1.1rem;
    font-weight: 800;
    letter-spacing: -0.02em;
  }

  .region-badge, .party-badge, .role-badge {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 8px;
    border: 1px solid #121212;
    text-transform: uppercase;
  }

  .region-badge { background: #a8dadc; }
  .party-badge { background: #ffb703; color: #121212; }
  .role-badge { background: #1d3557; color: #ffffff; }

  .nav-tabs {
    display: flex;
    gap: 4px;
    background: #e5e5e5;
    padding: 3px;
    border: 1px solid #121212;
  }

  .tab-btn {
    padding: 5px 12px;
    font-size: 0.78rem;
    font-weight: 800;
    border: none;
    background: transparent;
    cursor: pointer;
    transition: all 0.1s ease;
  }

  .tab-btn.active {
    background: #ffffff;
    border: 1px solid #121212;
    box-shadow: 1px 1px 0px #121212;
  }

  .tab-btn:hover:not(.active) { background: #f0f0f0; }

  .main-content {
    display: flex;
    flex: 1;
    position: relative;
    overflow: hidden;
  }

  /* Tavern Notice Board */
  .tavern-view, .expeditions-view {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .tavern-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .notice-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
    gap: 14px;
  }

  .notice-card {
    background: #ffffff;
    border: 2px solid #121212;
    box-shadow: 3px 3px 0px #121212;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .notice-type-tag {
    font-size: 0.65rem;
    font-weight: 800;
    text-transform: uppercase;
    padding: 2px 6px;
    border: 1px solid #121212;
    width: fit-content;
  }
  .notice-type-tag.bounty { background: #e63946; color: #fff; }
  .notice-type-tag.rumor { background: #457b9d; color: #fff; }
  .notice-type-tag.request { background: #2a9d8f; color: #fff; }

  .notice-title { font-size: 0.95rem; font-weight: 800; margin: 2px 0; }
  .notice-body { font-size: 0.8rem; color: #333; line-height: 1.35; }
  .notice-meta { font-size: 0.7rem; color: #666; margin-top: 4px; }
  .bounty-reward {
    font-size: 0.78rem;
    font-weight: 800;
    background: #fff3b0;
    padding: 3px 6px;
    border: 1px solid #121212;
    width: fit-content;
    margin-top: 4px;
  }

  /* Expedition Log Timeline */
  .log-table {
    width: 100%;
    border-collapse: collapse;
    border: 2px solid #121212;
    background: #ffffff;
    font-size: 0.8rem;
  }
  .log-table th, .log-table td {
    padding: 8px 12px;
    border: 1px solid #121212;
    text-align: left;
  }
  .log-table th { background: #fafafa; font-weight: 800; }
`;

export const westMarchesAtlasStyles = [
  baseAtlasStyles,
  mapStyles,
  pinStyles,
  strongholdStyles,
];
