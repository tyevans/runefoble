import { css } from 'lit';

export const factionRadarStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #121212);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    border-radius: var(--rf-border-radius, 0px);
    box-shadow: var(--rf-shadow, 4px 4px 0px var(--rf-shadow-color, #121212));
    padding: 20px;
    box-sizing: border-box;
    width: 100%;
    max-width: 960px;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
  }
  .title-group { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .title-group h3 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 900;
    letter-spacing: -0.02em;
    text-transform: uppercase;
  }
  .controls-group { display: flex; align-items: center; gap: 8px; }

  .badge {
    display: inline-flex;
    align-items: center;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    padding: 3px 8px;
    border: 1px solid var(--rf-border-color, #121212);
    letter-spacing: 0.05em;
  }
  .badge-tick { background: var(--rf-accent-tertiary, #ffb703); color: var(--rf-text-primary, #121212); }
  .badge-dm { background: var(--rf-accent-secondary, #1d3557); color: var(--rf-text-inverse, #ffffff); }
  .badge-player { background: var(--rf-bg-canvas, #f8f9fa); color: var(--rf-text-primary, #121212); }

  .btn {
    font-family: inherit;
    font-size: 0.78rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 6px 12px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    cursor: pointer;
    box-shadow: 2px 2px 0px var(--rf-shadow-color, #121212);
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .btn:hover { transform: translate(-1px, -1px); box-shadow: 3px 3px 0px var(--rf-shadow-color, #121212); }
  .btn:active { transform: translate(1px, 1px); box-shadow: 1px 1px 0px var(--rf-shadow-color, #121212); }
  .btn-primary { background: var(--rf-accent-primary, #e63946); color: var(--rf-text-inverse, #ffffff); }
  .btn-secondary { background: var(--rf-accent-secondary, #1d3557); color: var(--rf-text-inverse, #ffffff); }
  .btn-drawer.active { background: var(--rf-accent-secondary, #1d3557); color: var(--rf-text-inverse, #ffffff); }

  /* Grid Layout */
  .radar-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 20px;
  }
  @media (max-width: 768px) { .radar-grid { grid-template-columns: 1fr; } }

  /* Radar Chart */
  .radar-card {
    background: var(--rf-bg-canvas, #f8f9fa);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }
  .radar-title {
    font-size: 0.85rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
    align-self: flex-start;
  }
  .radar-svg { width: 100%; max-width: 320px; height: auto; overflow: visible; }
  .radar-axis-line { stroke: var(--rf-border-subtle, rgba(18, 18, 18, 0.2)); stroke-width: 1; stroke-dasharray: 2 2; }
  .radar-ring { fill: none; stroke: var(--rf-border-subtle, rgba(18, 18, 18, 0.2)); stroke-width: 1; }
  .radar-polygon {
    fill: rgba(230, 57, 70, 0.25);
    stroke: var(--rf-accent-primary, #e63946);
    stroke-width: 2.5;
    transition: all 0.3s ease;
  }
  .radar-node {
    fill: var(--rf-accent-primary, #e63946);
    stroke: var(--rf-bg-surface, #ffffff);
    stroke-width: 2;
    cursor: pointer;
    transition: r 0.15s ease;
  }
  .radar-node:hover { r: 6; }
  .radar-node.selected { fill: var(--rf-accent-secondary, #1d3557); r: 7; }
  .radar-label {
    font-family: inherit;
    font-size: 10px;
    font-weight: 700;
    fill: var(--rf-text-primary, #121212);
    text-anchor: middle;
    text-transform: uppercase;
  }

  /* Factions Roster */
  .factions-roster { display: flex; flex-direction: column; gap: 10px; max-height: 400px; overflow-y: auto; }
  .faction-card {
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 12px;
    box-sizing: border-box;
    cursor: pointer;
    transition: transform 0.1s ease, border-color 0.1s ease;
  }
  .faction-card:hover { border-color: var(--rf-accent-primary, #e63946); }
  .faction-card.selected {
    border-color: var(--rf-accent-secondary, #1d3557);
    border-left-width: 6px;
    background: var(--rf-bg-card, #ffffff);
  }
  .faction-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
  .faction-name { font-size: 0.95rem; font-weight: 800; text-transform: uppercase; }

  .disposition-badge {
    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
    padding: 2px 6px;
    border: 1px solid var(--rf-border-color, #121212);
  }
  .disposition-allied { background: var(--rf-accent-secondary, #1d3557); color: #ffffff; }
  .disposition-friendly { background: #2a9d8f; color: #ffffff; }
  .disposition-neutral { background: #e5e7eb; color: #121212; }
  .disposition-unfriendly { background: var(--rf-accent-tertiary, #ffb703); color: #121212; }
  .disposition-hostile { background: var(--rf-accent-primary, #e63946); color: #ffffff; }

  .faction-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; font-size: 0.75rem; }
  .chip-territory {
    background: var(--rf-bg-canvas, #f8f9fa);
    border: 1px solid var(--rf-border-color, #121212);
    padding: 2px 6px;
    font-weight: 700;
  }
  .metrics-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 6px; }
  .metric-bar-group { display: flex; flex-direction: column; gap: 2px; }
  .metric-label { display: flex; justify-content: space-between; font-size: 0.68rem; font-weight: 700; text-transform: uppercase; }
  .progress-track { width: 100%; height: 6px; background: #e5e7eb; border: 1px solid var(--rf-border-color, #121212); overflow: hidden; }
  .progress-fill { height: 100%; background: var(--rf-accent-primary, #e63946); transition: width 0.3s ease; }
  .progress-fill.resources { background: var(--rf-accent-secondary, #1d3557); }
  .progress-fill.goal { background: var(--rf-accent-tertiary, #ffb703); }
  .faction-goal {
    font-size: 0.75rem;
    line-height: 1.3;
    color: var(--rf-text-secondary, #2d3748);
    border-top: 1px dashed var(--rf-border-subtle, rgba(18, 18, 18, 0.2));
    padding-top: 6px;
    margin-top: 4px;
  }

  /* DM Secret Briefing Drawer */
  .dm-drawer {
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-accent-secondary, #1d3557);
    padding: 16px;
    margin-top: 16px;
    box-shadow: 4px 4px 0px var(--rf-accent-secondary, #1d3557);
  }
  .drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid var(--rf-accent-secondary, #1d3557);
    padding-bottom: 8px;
    margin-bottom: 12px;
  }
  .drawer-title {
    font-size: 1rem;
    font-weight: 900;
    text-transform: uppercase;
    color: var(--rf-accent-secondary, #1d3557);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .bulletin-content {
    font-family: var(--rf-font-mono, monospace);
    font-size: 0.82rem;
    line-height: 1.5;
    white-space: pre-wrap;
    background: var(--rf-bg-canvas, #f8f9fa);
    padding: 12px;
    border: 1px solid var(--rf-border-color, #121212);
    margin-bottom: 12px;
    max-height: 250px;
    overflow-y: auto;
  }
  .shifts-list { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
  .shift-card { background: #ffffff; border: 1px solid var(--rf-border-color, #121212); padding: 10px; }
  .shift-card-header { display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; font-weight: 800; margin-bottom: 4px; }
  .severity-badge { font-size: 0.65rem; font-weight: 800; text-transform: uppercase; padding: 2px 6px; border: 1px solid var(--rf-border-color, #121212); }
  .severity-critical { background: var(--rf-accent-primary, #e63946); color: #ffffff; }
  .severity-moderate { background: var(--rf-accent-tertiary, #ffb703); color: #121212; }
  .severity-minor { background: #e5e7eb; color: #121212; }
  .ripple-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
  .ripple-tag { font-size: 0.68rem; background: var(--rf-bg-canvas, #f8f9fa); border: 1px dashed var(--rf-border-color, #121212); padding: 2px 6px; }

  /* Redacted notice for non-DM */
  .redacted-box {
    background: #fef2f2;
    border: 2px dashed var(--rf-accent-primary, #e63946);
    padding: 16px;
    text-align: center;
    color: var(--rf-accent-primary, #e63946);
    font-weight: 800;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 16px;
  }

  /* Public Tavern Rumors Feed */
  .rumors-section {
    border-top: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-top: 16px;
    margin-top: 16px;
  }
  .rumors-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
  .rumors-header h4 { margin: 0; font-size: 0.95rem; font-weight: 900; text-transform: uppercase; letter-spacing: -0.01em; }
  .rumors-list { display: flex; flex-direction: column; gap: 8px; }
  .rumor-item {
    background: var(--rf-bg-canvas, #f8f9fa);
    border: 1px solid var(--rf-border-color, #121212);
    padding: 10px 12px;
    font-size: 0.82rem;
    line-height: 1.4;
    font-style: italic;
    border-left: 4px solid var(--rf-accent-tertiary, #ffb703);
  }
  .empty-state {
    padding: 24px;
    text-align: center;
    color: var(--rf-text-muted, #6b7280);
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
  }
`;
