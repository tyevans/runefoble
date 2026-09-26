import { css } from 'lit';

export const initiativeTrackerStyles = css`
  :host {
    display: block; font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary); background: var(--rf-bg-canvas);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow); box-sizing: border-box;
    padding: 16px; width: 100%; max-width: 440px;
  }
  .header {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
    padding-bottom: 12px; margin-bottom: 12px;
  }
  .title { font-size: 1.1rem; font-weight: 900; letter-spacing: 0.05em; text-transform: uppercase; margin: 0; }
  .status-badge {
    display: inline-block; font-size: 0.65rem; font-weight: 800; letter-spacing: 0.08em;
    text-transform: uppercase; padding: 2px 6px; border: 1px solid var(--rf-border-color);
    background: var(--rf-bg-surface); margin-top: 2px;
  }
  .status-badge.in-combat { background: var(--rf-accent-primary); color: var(--rf-text-inverse); }
  .round-badge {
    background: var(--rf-accent-tertiary); border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm); padding: 4px 10px; font-weight: 900; font-size: 0.95rem; text-transform: uppercase;
  }
  .timer-section {
    background: var(--rf-bg-surface); border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    padding: 10px 12px; margin-bottom: 14px; box-shadow: var(--rf-shadow-sm);
  }
  .timer-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
  .timer-label { font-size: 0.75rem; font-weight: 800; text-transform: uppercase; color: var(--rf-text-muted); }
  .timer-digits { font-family: ui-monospace, SFMono-Regular, monospace; font-size: 1.35rem; font-weight: 900; }
  .timer-digits.urgent { color: var(--rf-accent-primary); animation: pulse 1s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  .progress-bar-bg { height: 8px; background: var(--rf-bg-inset); border: 1px solid var(--rf-border-color); overflow: hidden; margin-bottom: 8px; }
  .progress-bar-fill { height: 100%; background: var(--rf-accent-secondary); transition: width 0.3s ease; }
  .progress-bar-fill.urgent { background: var(--rf-accent-primary); }
  .timer-actions { display: flex; gap: 6px; justify-content: flex-end; }
  .btn-sm {
    font-size: 0.7rem; font-weight: 800; padding: 3px 8px;
    background: var(--rf-bg-canvas); border: 1px solid var(--rf-border-color);
    cursor: pointer; text-transform: uppercase;
  }
  .btn-sm:hover { background: var(--rf-bg-surface); }
  .btn-sm:active { transform: translate(1px, 1px); }
  .active-banner {
    background: var(--rf-accent-primary); color: var(--rf-text-inverse);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm); padding: 8px 12px; margin-bottom: 12px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .active-tag { font-size: 0.65rem; font-weight: 900; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.9; }
  .active-name { font-size: 1.15rem; font-weight: 900; display: block; }
  .active-stats { font-size: 0.8rem; font-weight: 800; text-align: right; }
  .order-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; max-height: 280px; overflow-y: auto; }
  .order-item {
    display: flex; align-items: center; gap: 8px; padding: 8px 10px;
    background: var(--rf-bg-surface); border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm); cursor: pointer;
    transition: background-color 0.15s ease, transform 0.05s ease;
  }
  .order-item:hover { background: var(--rf-bg-canvas); }
  .order-item.active { background: var(--rf-bg-canvas); border-color: var(--rf-accent-primary); transform: translateX(4px); }
  .rank-box {
    width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;
    font-weight: 900; font-size: 0.75rem; background: var(--rf-border-color); color: var(--rf-text-inverse); border: 1px solid var(--rf-border-color);
  }
  .score-badge {
    background: var(--rf-accent-tertiary); color: var(--rf-color-dark);
    font-weight: 900; font-size: 0.8rem; padding: 2px 6px;
    border: 1px solid var(--rf-border-color); min-width: 22px; text-align: center;
  }
  .combatant-details { flex: 1; display: flex; align-items: center; justify-content: space-between; }
  .combatant-name { font-weight: 800; font-size: 0.9rem; }
  .npc-tag {
    font-size: 0.65rem; font-weight: 800; text-transform: uppercase;
    padding: 1px 5px; border: 1px solid var(--rf-border-color); background: var(--rf-bg-inset); color: var(--rf-text-muted);
  }
  .empty-state {
    padding: 20px; text-align: center; font-size: 0.85rem; font-weight: 700;
    color: var(--rf-text-muted); border: 2px dashed var(--rf-border-color);
  }
  .controls { display: flex; gap: 8px; }
  .btn-main {
    flex: 1; background: var(--rf-accent-primary); color: var(--rf-text-inverse);
    font-weight: 900; font-size: 0.95rem; text-transform: uppercase; padding: 10px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm); cursor: pointer;
  }
  .btn-main:hover { filter: brightness(0.9); }
  .btn-main:active { transform: translate(2px, 2px); box-shadow: none; }
  .btn-secondary {
    background: var(--rf-bg-surface); color: var(--rf-text-primary);
    font-weight: 800; font-size: 0.85rem; padding: 10px 14px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm); cursor: pointer; text-transform: uppercase;
  }
  .btn-secondary:hover { background: var(--rf-bg-canvas); }
  .btn-secondary:active { transform: translate(2px, 2px); box-shadow: none; }
`;
