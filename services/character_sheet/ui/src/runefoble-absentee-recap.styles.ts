import { css } from 'lit';

export const absenteeRecapStyles = css`
  :host {
    display: block;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(145deg, #111827 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 24px;
    color: #f8fafc;
    max-width: 580px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
    position: relative;
    overflow: hidden;
  }
  .modal-glow {
    position: absolute;
    top: -60px;
    right: -60px;
    width: 140px;
    height: 140px;
    background: radial-gradient(circle, rgba(168, 85, 247, 0.25) 0%, rgba(0, 0, 0, 0) 70%);
    pointer-events: none;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 14px;
  }
  .title-area h2 {
    font-size: 1.35rem;
    margin: 0 0 4px 0;
    color: #f1f5f9;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .hero-meta { font-size: 0.85rem; color: #94a3b8; }
  .persona-tag {
    background: #1e1b4b;
    color: #a5b4fc;
    border: 1px solid #4338ca;
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 9999px;
    font-weight: 600;
    text-transform: capitalize;
  }
  .penalties-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  .penalty-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 8px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .penalty-drunk { background: #78350f; color: #fef3c7; border: 1px solid #d97706; box-shadow: 0 0 8px rgba(217, 119, 6, 0.3); }
  .penalty-foolishness { background: #581c87; color: #f3e8ff; border: 1px solid #c084fc; box-shadow: 0 0 8px rgba(192, 132, 252, 0.3); }
  .penalty-greed { background: #14532d; color: #dcfce7; border: 1px solid #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.3); }
  .penalty-cowardice { background: #1e293b; color: #cbd5e1; border: 1px solid #64748b; }
  .penalty-default { background: #7f1d1d; color: #fee2e2; border: 1px solid #ef4444; }
  .status-strip {
    display: flex; gap: 12px; margin-bottom: 16px;
    background: #090d16; border: 1px solid #1e293b;
    padding: 10px 14px; border-radius: 10px; font-size: 0.82rem;
  }
  .status-item { display: flex; align-items: center; gap: 6px; }
  .hp-positive { color: #4ade80; font-weight: 700; }
  .hp-negative { color: #f87171; font-weight: 700; }
  .hp-neutral { color: #94a3b8; }
  .narrative-box {
    background: #1e293b44; border-left: 3px solid #8b5cf6;
    padding: 14px 16px; border-radius: 0 8px 8px 0; font-size: 0.92rem;
    line-height: 1.55; color: #e2e8f0; margin-bottom: 18px; font-style: italic;
  }
  .section-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; font-weight: 700; margin-bottom: 8px; }
  .highlights-list { list-style: none; padding: 0; margin: 0 0 20px 0; display: flex; flex-direction: column; gap: 8px; }
  .highlight-item {
    display: flex; align-items: flex-start; gap: 8px; font-size: 0.85rem;
    color: #cbd5e1; line-height: 1.4; background: #0f172a66; border: 1px solid #1e293b;
    padding: 8px 12px; border-radius: 8px;
  }
  .highlight-icon { color: #f59e0b; font-size: 0.95rem; flex-shrink: 0; }
  .audio-player-bar {
    display: flex; align-items: center; justify-content: space-between;
    background: #0b0f19; border: 1px solid #334155; border-radius: 12px;
    padding: 12px 16px; gap: 14px;
  }
  .play-btn {
    background: #6366f1; color: #ffffff; border: none; border-radius: 8px;
    padding: 8px 16px; font-weight: 600; font-size: 0.85rem; cursor: pointer;
    display: inline-flex; align-items: center; gap: 8px; transition: all 0.2s ease;
  }
  .play-btn:hover { background: #4f46e5; }
  .play-btn.playing { background: #dc2626; }
  .play-btn.playing:hover { background: #b91c1c; }
  .audio-info { flex: 1; display: flex; flex-direction: column; gap: 4px; }
  .audio-title { font-size: 0.8rem; font-weight: 600; color: #f1f5f9; }
  .audio-subtitle { font-size: 0.72rem; color: #64748b; }
  .audio-waveform { display: flex; align-items: flex-end; gap: 3px; height: 20px; }
  .wave-bar { width: 3px; background: #6366f1; border-radius: 2px; animation: pulse 1s infinite alternate ease-in-out; }
  .wave-bar:nth-child(2) { animation-delay: 0.2s; }
  .wave-bar:nth-child(3) { animation-delay: 0.4s; }
  .wave-bar:nth-child(4) { animation-delay: 0.1s; }
  .wave-bar:nth-child(5) { animation-delay: 0.3s; }
  @keyframes pulse { 0% { height: 4px; } 100% { height: 18px; } }
`;
