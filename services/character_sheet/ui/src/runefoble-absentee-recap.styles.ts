import { css } from 'lit';

export const absenteeRecapStyles = css`
  :host {
    display: block; font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-card); border: var(--rf-border-width, 1px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 8px); padding: 24px; color: var(--rf-text-primary);
    max-width: 580px; box-shadow: var(--rf-shadow); position: relative; overflow: hidden; box-sizing: border-box;
  }
  .modal-glow {
    position: absolute; top: -60px; right: -60px; width: 140px; height: 140px;
    background: radial-gradient(circle, rgba(168, 85, 247, 0.25) 0%, rgba(0, 0, 0, 0) 70%);
    pointer-events: none;
  }
  .header {
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 16px; border-bottom: 1px solid var(--rf-border-subtle); padding-bottom: 14px;
  }
  .title-area h2 {
    font-size: 1.35rem; margin: 0 0 4px 0; color: var(--rf-text-primary);
    display: flex; align-items: center; gap: 8px;
  }
  .hero-meta { font-size: 0.85rem; color: var(--rf-text-muted); }
  .persona-tag {
    background: var(--rf-bg-inset); color: var(--rf-accent-secondary);
    border: 1px solid var(--rf-border-subtle); font-size: 0.75rem;
    padding: 2px 8px; border-radius: 9999px; font-weight: 600; text-transform: capitalize;
  }
  .penalties-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  .penalty-badge {
    display: inline-flex; align-items: center; gap: 6px; font-size: 0.75rem;
    font-weight: 700; padding: 4px 10px; border-radius: var(--rf-border-radius, 8px);
    text-transform: uppercase; letter-spacing: 0.04em;
  }
  .penalty-drunk { background: var(--rf-accent-tertiary); color: var(--rf-color-dark); border: 1px solid var(--rf-border-color); box-shadow: var(--rf-shadow-sm); }
  .penalty-foolishness { background: var(--rf-accent-secondary); color: var(--rf-text-inverse); border: 1px solid var(--rf-border-color); box-shadow: var(--rf-shadow-sm); }
  .penalty-greed { background: var(--rf-accent-primary); color: var(--rf-text-inverse); border: 1px solid var(--rf-border-color); box-shadow: var(--rf-shadow-sm); }
  .penalty-cowardice { background: var(--rf-bg-inset); color: var(--rf-text-muted); border: 1px solid var(--rf-border-subtle); }
  .penalty-default { background: var(--rf-accent-primary); color: var(--rf-text-inverse); border: 1px solid var(--rf-border-color); }
  .status-strip {
    display: flex; gap: 12px; margin-bottom: 16px; background: var(--rf-bg-inset);
    border: 1px solid var(--rf-border-subtle); padding: 10px 14px; border-radius: 10px; font-size: 0.82rem;
  }
  .status-item { display: flex; align-items: center; gap: 6px; }
  .hp-positive { color: var(--rf-accent-secondary); font-weight: 700; }
  .hp-negative { color: var(--rf-accent-primary); font-weight: 700; }
  .hp-neutral { color: var(--rf-text-muted); }
  .narrative-box {
    background: var(--rf-bg-inset); border-left: 3px solid var(--rf-accent-secondary);
    padding: 14px 16px; border-radius: 0 8px 8px 0; font-size: 0.92rem;
    line-height: 1.55; color: var(--rf-text-secondary); margin-bottom: 18px; font-style: italic;
  }
  .section-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--rf-text-muted); font-weight: 700; margin-bottom: 8px; }
  .highlights-list { list-style: none; padding: 0; margin: 0 0 20px 0; display: flex; flex-direction: column; gap: 8px; }
  .highlight-item {
    display: flex; align-items: flex-start; gap: 8px; font-size: 0.85rem;
    color: var(--rf-text-secondary); line-height: 1.4; background: var(--rf-bg-inset);
    border: 1px solid var(--rf-border-subtle); padding: 8px 12px; border-radius: 8px;
  }
  .highlight-icon { color: var(--rf-accent-tertiary); font-size: 0.95rem; flex-shrink: 0; }
  .audio-player-bar {
    display: flex; align-items: center; justify-content: space-between;
    background: var(--rf-bg-inset); border: 1px solid var(--rf-border-subtle);
    border-radius: 12px; padding: 12px 16px; gap: 14px;
  }
  .play-btn {
    background: var(--rf-accent-secondary); color: var(--rf-text-inverse);
    border: var(--rf-border-width, 1px) solid var(--rf-border-color); border-radius: var(--rf-border-radius, 8px);
    padding: 8px 16px; font-weight: 600; font-size: 0.85rem; cursor: pointer;
    display: inline-flex; align-items: center; gap: 8px; transition: all 0.2s ease;
  }
  .play-btn:hover { filter: brightness(0.9); }
  .play-btn.playing { background: var(--rf-accent-primary); }
  .play-btn.playing:hover { filter: brightness(0.9); }
  .audio-info { flex: 1; display: flex; flex-direction: column; gap: 4px; }
  .audio-title { font-size: 0.8rem; font-weight: 600; color: var(--rf-text-primary); }
  .audio-subtitle { font-size: 0.72rem; color: var(--rf-text-muted); }
  .audio-waveform { display: flex; align-items: flex-end; gap: 3px; height: 20px; }
  .wave-bar { width: 3px; background: var(--rf-accent-secondary); border-radius: 2px; animation: pulse 1s infinite alternate ease-in-out; }
  .wave-bar:nth-child(2) { animation-delay: 0.2s; }
  .wave-bar:nth-child(3) { animation-delay: 0.4s; }
  .wave-bar:nth-child(4) { animation-delay: 0.1s; }
  .wave-bar:nth-child(5) { animation-delay: 0.3s; }
  @keyframes pulse { 0% { height: 4px; } 100% { height: 18px; } }
`;
