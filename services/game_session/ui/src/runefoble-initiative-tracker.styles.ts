import { css } from 'lit';

export const initiativeTrackerStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #121212);
    background: var(--rf-bg-canvas, #f8f9fa);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    box-sizing: border-box;
    padding: 16px;
    width: 100%;
    max-width: 440px;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 12px;
    margin-bottom: 12px;
  }
  .title { font-size: 1.1rem; font-weight: 900; letter-spacing: 0.05em; text-transform: uppercase; margin: 0; }
  .status-badge {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 6px;
    border: 1px solid var(--rf-border-color, #121212);
    background: var(--rf-bg-surface, #ffffff);
    margin-top: 2px;
  }
  .status-badge.in-combat { background: var(--rf-accent-red, #d62828); color: #ffffff; }
  .round-badge {
    background: var(--rf-accent-yellow, #fcbf49);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: 2px 2px 0px #121212;
    padding: 4px 10px;
    font-weight: 900;
    font-size: 0.95rem;
    text-transform: uppercase;
  }
  .timer-section {
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 10px 12px;
    margin-bottom: 14px;
    box-shadow: 2px 2px 0px #121212;
  }
  .timer-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
  .timer-label { font-size: 0.75rem; font-weight: 800; text-transform: uppercase; color: var(--rf-text-muted, #4b5563); }
  .timer-digits { font-family: ui-monospace, SFMono-Regular, monospace; font-size: 1.35rem; font-weight: 900; }
  .timer-digits.urgent { color: var(--rf-accent-red, #d62828); animation: pulse 1s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  .progress-bar-bg { height: 8px; background: #e5e7eb; border: 1px solid var(--rf-border-color, #121212); overflow: hidden; margin-bottom: 8px; }
  .progress-bar-fill { height: 100%; background: var(--rf-accent-blue, #00509d); transition: width 0.3s ease; }
  .progress-bar-fill.urgent { background: var(--rf-accent-red, #d62828); }
  .timer-actions { display: flex; gap: 6px; justify-content: flex-end; }
  .btn-sm {
    font-size: 0.7rem; font-weight: 800; padding: 3px 8px;
    background: var(--rf-bg-canvas, #f8f9fa); border: 1px solid var(--rf-border-color, #121212);
    cursor: pointer; text-transform: uppercase;
  }
  .btn-sm:hover { background: #e5e7eb; }
  .btn-sm:active { transform: translate(1px, 1px); }
  .active-banner {
    background: var(--rf-accent-red, #d62828); color: #ffffff;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: 2px 2px 0px #121212; padding: 8px 12px; margin-bottom: 12px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .active-tag { font-size: 0.65rem; font-weight: 900; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.9; }
  .active-name { font-size: 1.15rem; font-weight: 900; display: block; }
  .active-stats { font-size: 0.8rem; font-weight: 800; text-align: right; }
  .order-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; max-height: 280px; overflow-y: auto; }
  .order-item {
    display: flex; align-items: center; gap: 8px; padding: 8px 10px;
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: 2px 2px 0px #121212; cursor: pointer;
    transition: background-color 0.15s ease, transform 0.05s ease;
  }
  .order-item:hover { background: #fdf0ed; }
  .order-item.active { background: #fee2e2; border-color: var(--rf-accent-red, #d62828); transform: translateX(4px); }
  .rank-box {
    width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;
    font-weight: 900; font-size: 0.75rem; background: #121212; color: #ffffff; border: 1px solid #121212;
  }
  .score-badge {
    background: var(--rf-accent-yellow, #fcbf49); color: #121212;
    font-weight: 900; font-size: 0.8rem; padding: 2px 6px;
    border: 1px solid #121212; min-width: 22px; text-align: center;
  }
  .combatant-details { flex: 1; display: flex; align-items: center; justify-content: space-between; }
  .combatant-name { font-weight: 800; font-size: 0.9rem; }
  .npc-tag {
    font-size: 0.65rem; font-weight: 800; text-transform: uppercase;
    padding: 1px 5px; border: 1px solid #121212; background: #e5e7eb;
  }
  .empty-state {
    padding: 20px; text-align: center; font-size: 0.85rem; font-weight: 700;
    color: var(--rf-text-muted, #4b5563); border: 2px dashed var(--rf-border-color, #121212);
  }
  .controls { display: flex; gap: 8px; }
  .btn-main {
    flex: 1; background: var(--rf-accent-red, #d62828); color: #ffffff;
    font-weight: 900; font-size: 0.95rem; text-transform: uppercase; padding: 10px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: 2px 2px 0px #121212; cursor: pointer;
  }
  .btn-main:hover { background: #b91c1c; }
  .btn-main:active { transform: translate(2px, 2px); box-shadow: 0px 0px 0px #121212; }
  .btn-secondary {
    background: var(--rf-bg-surface, #ffffff); color: var(--rf-text-primary, #121212);
    font-weight: 800; font-size: 0.85rem; padding: 10px 14px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: 2px 2px 0px #121212; cursor: pointer; text-transform: uppercase;
  }
  .btn-secondary:hover { background: #f3f4f6; }
  .btn-secondary:active { transform: translate(2px, 2px); box-shadow: 0px 0px 0px #121212; }
`;
