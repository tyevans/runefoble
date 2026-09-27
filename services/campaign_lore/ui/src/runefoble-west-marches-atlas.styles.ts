import { css } from 'lit';

export const westMarchesAtlasStyles = css`
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

  /* Map Viewport */
  .map-wrapper {
    flex: 1;
    position: relative;
    background: #f4f6f8;
    overflow: hidden;
    cursor: grab;
    user-select: none;
  }

  .map-wrapper:active { cursor: grabbing; }

  .map-svg {
    width: 100%;
    height: 100%;
    position: absolute;
    top: 0;
    left: 0;
  }

  .frontier-grid { stroke: #e0e0e0; stroke-width: 1px; }

  .outpost-marker, .pin-marker { cursor: pointer; }
  .outpost-circle { fill: #2a9d8f; stroke: #121212; stroke-width: 2.5px; }
  .pin-marker:hover { transform: scale(1.3); }
  .pin-circle { stroke: #121212; stroke-width: 2px; }

  .pin-tag {
    font-size: 10px;
    font-weight: 800;
    fill: #121212;
    text-shadow: 1px 1px 0px #fff, -1px -1px 0px #fff;
    pointer-events: none;
  }

  .pin-danger {
    font-size: 8px;
    font-weight: 900;
    fill: #ffffff;
    text-anchor: middle;
    pointer-events: none;
  }

  /* Popover Floating Inspection Card */
  .inspection-popover {
    position: absolute;
    bottom: 20px;
    right: 20px;
    width: 320px;
    background: #ffffff;
    border: 2px solid #121212;
    box-shadow: 4px 4px 0px #121212;
    padding: 14px;
    z-index: 25;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .popover-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .popover-title { font-size: 1rem; font-weight: 800; margin: 0; }
  .popover-close { background: transparent; border: none; font-weight: 800; font-size: 1.1rem; cursor: pointer; }

  .badge-row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .type-badge, .danger-badge, .attribution-badge {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 6px;
    border: 1px solid #121212;
  }
  .type-badge { background: #f1faee; text-transform: uppercase; }
  .danger-badge { background: #e63946; color: #ffffff; font-weight: 800; }
  .attribution-badge { background: #ffb703; }

  .popover-desc { font-size: 0.8rem; color: #333; line-height: 1.35; }
  .popover-notes { font-size: 0.76rem; padding: 6px 8px; background: #f8f9fa; border-left: 3px solid #457b9d; color: #444; }
  .zanzibar-notice { font-size: 0.68rem; font-style: italic; color: #666; background: #fefae0; padding: 4px 6px; border: 1px dashed #d4a373; }

  .map-controls {
    position: absolute;
    bottom: 16px;
    left: 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    z-index: 10;
  }

  .map-btn {
    width: 32px;
    height: 32px;
    font-size: 1.1rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #ffffff;
    border: 2px solid #121212;
    box-shadow: 2px 2px 0px #121212;
    cursor: pointer;
  }

  .filter-panel {
    position: absolute;
    top: 14px;
    left: 14px;
    background: #ffffff;
    border: 2px solid #121212;
    box-shadow: 3px 3px 0px #121212;
    padding: 10px;
    z-index: 10;
    display: flex;
    gap: 8px;
    align-items: center;
    font-size: 0.78rem;
  }

  .filter-select {
    padding: 4px 8px;
    font-size: 0.75rem;
    font-weight: 700;
    border: 1px solid #121212;
    background: #fafafa;
  }

  /* Stronghold Dashboard */
  .stronghold-view, .tavern-view, .expeditions-view {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .dashboard-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 18px;
    background: #1d3557;
    color: #ffffff;
    border: 2px solid #121212;
    box-shadow: 3px 3px 0px #121212;
  }

  .banner-text h3 { margin: 0 0 4px 0; font-size: 1.15rem; }
  .banner-meta { font-size: 0.8rem; opacity: 0.9; }

  .facility-grid, .notice-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
    gap: 14px;
  }

  .facility-card, .notice-card {
    background: #ffffff;
    border: 2px solid #121212;
    box-shadow: 3px 3px 0px #121212;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .facility-header { display: flex; justify-content: space-between; align-items: center; }
  .facility-title { font-size: 0.95rem; font-weight: 800; }
  .facility-tier-badge { font-size: 0.7rem; font-weight: 800; padding: 2px 8px; border: 1px solid #121212; background: #ffb703; }
  .boons-list { margin: 4px 0; padding-left: 18px; font-size: 0.78rem; color: #2b2b2b; }

  .upgrade-btn {
    align-self: flex-start;
    margin-top: 4px;
    padding: 6px 12px;
    font-size: 0.75rem;
    font-weight: 800;
    border: 1px solid #121212;
    background: #2a9d8f;
    color: #ffffff;
    cursor: pointer;
    box-shadow: 1px 1px 0px #121212;
  }
  .upgrade-btn:hover { transform: translate(-1px, -1px); box-shadow: 2px 2px 0px #121212; }

  /* Tavern Notice Board */
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
