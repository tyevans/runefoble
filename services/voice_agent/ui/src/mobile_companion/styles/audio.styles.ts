import { css } from 'lit';

export const audioStyles = css`
  :host {
    display: block;
  }

  .audio-status-card {
    background: var(--rf-bg-canvas, #f3f4f6);
    border: 1px solid var(--rf-border-color, #111111);
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .channel-indicator {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    padding-bottom: 4px;
    border-bottom: 1px dashed var(--rf-border-color, #d1d5db);
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--rf-text-secondary, #374151);
  }

  .channel-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #3b82f6;
    display: inline-block;
  }

  .status-line {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.82rem;
  }

  .status-label {
    font-weight: 600;
    color: var(--rf-text-muted, #4b5563);
  }

  .status-value {
    font-family: monospace;
    font-weight: 700;
  }

  .status-value.buffer-warn {
    color: #dc2626;
  }

  .status-value.buffer-ok {
    color: #15803d;
  }

  .bitrate-select {
    font-size: 0.75rem;
    font-family: monospace;
    padding: 2px 4px;
    border: 1px solid var(--rf-border-color, #111111);
    border-radius: 2px;
  }

  .buffer-bar-container {
    width: 100%;
    height: 6px;
    background: #e5e7eb;
    border: 1px solid var(--rf-border-color, #111111);
    border-radius: 2px;
    overflow: hidden;
    margin: 2px 0;
  }

  .buffer-bar {
    height: 100%;
    transition: width 0.2s ease, background-color 0.2s ease;
  }

  .buffer-bar.ok {
    background: #22c55e;
  }

  .buffer-bar.warn {
    background: #ef4444;
  }

  .mute-btn {
    font-size: 0.72rem;
    padding: 2px 6px;
    cursor: pointer;
    border: 1px solid var(--rf-border-color, #111111);
    background: #ffffff;
  }

  .mute-btn.muted {
    background: #f87171;
    color: #450a0a;
  }
`;
