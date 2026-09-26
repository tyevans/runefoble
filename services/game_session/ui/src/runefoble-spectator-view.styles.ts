import { css } from 'lit';

export const spectatorViewStyles = css`
  :host {
    display: flex; flex-direction: column;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary); background: var(--rf-bg-canvas);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow); box-sizing: border-box;
    padding: 16px; gap: 16px; width: 100%; max-width: 1080px;
    margin: 0 auto; user-select: none;
    transition: background-color 0.2s ease, border-color 0.2s ease;
  }
  :host([transparent-mode]) { background: transparent; box-shadow: none; }
  .stream-header {
    display: flex; justify-content: space-between; align-items: center;
    background: var(--rf-bg-surface); border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    padding: 10px 16px; box-shadow: var(--rf-shadow-sm); flex-wrap: wrap; gap: 12px;
  }
  .brand-group { display: flex; align-items: center; gap: 12px; }
  .live-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--rf-accent-primary); color: var(--rf-text-inverse);
    font-size: 0.75rem; font-weight: 800; padding: 3px 8px; letter-spacing: 0.5px;
    border: 1px solid var(--rf-border-color);
  }
  .live-dot {
    width: 8px; height: 8px; background: var(--rf-text-inverse); border-radius: 50%; animation: pulse 1.5s infinite;
  }
  @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.85); } }
  .session-title { font-size: 1.05rem; font-weight: 900; letter-spacing: -0.3px; }
  .round-pill {
    background: var(--rf-accent-secondary); color: var(--rf-text-inverse);
    font-size: 0.75rem; font-weight: 700; padding: 3px 8px; border: 1px solid var(--rf-border-color);
  }
  .atmosphere-bar {
    display: flex; align-items: center; gap: 12px; background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    padding: 8px 14px; box-shadow: var(--rf-shadow-sm); font-size: 0.85rem; flex-wrap: wrap;
  }
  .scene-tag { font-weight: 800; color: var(--rf-accent-secondary); display: flex; align-items: center; gap: 4px; }
  .scene-meta { color: var(--rf-text-muted); font-size: 0.8rem; }
  .audio-visualizer { display: inline-flex; align-items: flex-end; gap: 3px; height: 14px; margin-left: auto; }
  .audio-bar {
    width: 3px; background: var(--rf-accent-tertiary);
    border: 1px solid var(--rf-border-color); animation: audioJump 1.2s ease-in-out infinite alternate;
  }
  .audio-bar:nth-child(2) { animation-delay: 0.2s; height: 10px; }
  .audio-bar:nth-child(3) { animation-delay: 0.4s; height: 14px; }
  .audio-bar:nth-child(4) { animation-delay: 0.1s; height: 8px; }
  @keyframes audioJump { 0% { height: 4px; } 100% { height: 14px; } }
  .board-container {
    display: flex; justify-content: center; background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow); padding: 18px; overflow-x: auto;
  }
  .grid {
    display: grid; gap: 2px; background: var(--rf-border-color);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color); pointer-events: none;
  }
  .cell {
    width: 52px; height: 52px; background: var(--rf-bg-canvas);
    position: relative; display: flex; align-items: center; justify-content: center; box-sizing: border-box;
  }
  .token {
    width: 44px; height: 44px; border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm); display: flex; flex-direction: column;
    align-items: center; justify-content: center; color: var(--rf-text-inverse); font-weight: 800; font-size: 0.75rem;
    position: relative; transition: transform 0.25s ease;
  }
  .token.active-turn { outline: 3px solid var(--rf-accent-primary); outline-offset: 2px; }
  .token-label {
    font-size: 0.65rem; background: var(--rf-color-dark); color: var(--rf-text-inverse);
    padding: 1px 3px; white-space: nowrap; position: absolute; bottom: -8px;
    left: 50%; transform: translateX(-50%); pointer-events: none;
    border: 1px solid var(--rf-border-color);
  }
  .token-condition {
    position: absolute; top: -6px; right: -6px; background: var(--rf-accent-tertiary);
    color: var(--rf-color-dark); border: 1px solid var(--rf-border-color);
    font-size: 0.55rem; font-weight: 800; padding: 1px 3px;
  }
  .chronicle-ticker {
    display: flex; align-items: stretch; background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm); min-height: 48px; overflow: hidden;
  }
  .ticker-label {
    background: var(--rf-accent-tertiary); color: var(--rf-color-dark);
    font-weight: 900; font-size: 0.75rem; padding: 10px 14px; display: flex;
    align-items: center; gap: 6px; border-right: var(--rf-border-width, 2px) solid var(--rf-border-color);
    white-space: nowrap;
  }
  .ticker-stream {
    flex: 1; display: flex; align-items: center; padding: 8px 14px;
    gap: 16px; overflow-x: auto; font-size: 0.85rem;
  }
  .ticker-item {
    display: inline-flex; align-items: center; gap: 6px; white-space: nowrap;
    background: var(--rf-bg-canvas); border: 1px solid var(--rf-border-color); padding: 4px 8px;
  }
  .speaker-tag { font-weight: 800; color: var(--rf-accent-secondary); }
`;
