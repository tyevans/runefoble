import { css } from 'lit';

export const mobileCompanionStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #111111);
    box-sizing: border-box;
  }

  .companion-container {
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #111111);
    border-radius: var(--rf-border-radius, 4px);
    box-shadow: var(--rf-shadow, 4px 4px 0px rgba(0, 0, 0, 0.9));
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    max-width: 480px;
    margin: 0 auto;
    user-select: none;
  }

  .companion-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid var(--rf-border-color, #111111);
    padding-bottom: 10px;
  }

  .title-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .device-icon {
    font-size: 1.25rem;
  }

  .title-text {
    font-weight: 800;
    font-size: 1.05rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .badge-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .badge {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 8px;
    border: 1px solid var(--rf-border-color, #111111);
    border-radius: 2px;
    text-transform: uppercase;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .badge.connected {
    background: #4ade80;
    color: #064e3b;
  }

  .badge.disconnected {
    background: #f87171;
    color: #450a0a;
  }

  .badge.cellular {
    background: #fef08a;
    color: #713f12;
  }

  .badge.haptic {
    background: #c084fc;
    color: #3b0764;
  }

  .channel-indicator {
    display: flex;
    align-items: center;
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
  }

  .audio-status-card {
    background: var(--rf-bg-canvas, #f3f4f6);
    border: 1px solid var(--rf-border-color, #111111);
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .status-line {
    display: flex;
    justify-content: space-between;
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

  .whisper-card {
    background: #1e1b4b;
    color: #e0e7ff;
    border: 2px solid #818cf8;
    border-radius: 4px;
    padding: 14px;
    box-shadow: 0 0 12px rgba(129, 140, 248, 0.4);
    animation: whisper-glow 2s infinite alternate;
    position: relative;
  }

  @keyframes whisper-glow {
    0% {
      border-color: #818cf8;
      box-shadow: 0 0 8px rgba(129, 140, 248, 0.3);
    }
    100% {
      border-color: #c084fc;
      box-shadow: 0 0 16px rgba(192, 132, 252, 0.6);
    }
  }

  .whisper-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 800;
    font-size: 0.85rem;
    text-transform: uppercase;
    color: #a5b4fc;
    margin-bottom: 8px;
  }

  .whisper-body {
    position: relative;
    font-style: italic;
    font-size: 0.95rem;
    line-height: 1.4;
    cursor: pointer;
    min-height: 2.4em;
    display: flex;
    align-items: center;
    user-select: text;
  }

  .whisper-body.content-blurred {
    filter: blur(6px);
    user-select: none;
    opacity: 0.7;
    transition: filter 0.2s ease, opacity 0.2s ease;
  }

  .blur-overlay-hint {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.8rem;
    color: #fef08a;
    background: rgba(30, 27, 75, 0.55);
    border: 1px dashed #fef08a;
    border-radius: 2px;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    z-index: 2;
  }

  .whisper-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 10px;
  }

  .turn-card {
    background: #7f1d1d;
    color: #fef2f2;
    border: 2px solid #f87171;
    border-radius: 4px;
    padding: 12px;
    animation: turn-pulse 1s infinite alternate;
  }

  @keyframes turn-pulse {
    0% {
      transform: scale(1);
    }
    100% {
      transform: scale(1.01);
    }
  }

  .turn-title {
    font-weight: 900;
    font-size: 1rem;
    text-transform: uppercase;
  }

  .btn {
    border: 2px solid var(--rf-border-color, #111111);
    font-weight: 700;
    font-size: 0.85rem;
    padding: 6px 12px;
    cursor: pointer;
    background: #ffffff;
    color: #111111;
    box-shadow: 2px 2px 0px rgba(0, 0, 0, 0.8);
    transition: transform 0.08s ease, box-shadow 0.08s ease;
  }

  .btn:active {
    transform: translate(2px, 2px);
    box-shadow: 0px 0px 0px rgba(0, 0, 0, 0.8);
  }

  .btn-xs {
    font-size: 0.72rem;
    padding: 2px 6px;
    box-shadow: 1px 1px 0px rgba(0, 0, 0, 0.8);
  }

  .btn-ptt {
    background: #2563eb;
    color: #ffffff;
    font-size: 1.05rem;
    padding: 16px;
    text-align: center;
    text-transform: uppercase;
    font-weight: 900;
    letter-spacing: 0.5px;
    border-radius: 4px;
    touch-action: none;
    box-shadow: 3px 3px 0px rgba(0, 0, 0, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }

  .btn-ptt:hover {
    background: #1d4ed8;
  }

  .btn-ptt.active {
    background: #dc2626;
    animation: ptt-glow 0.8s infinite alternate;
    box-shadow: inset 2px 2px 4px rgba(0, 0, 0, 0.4);
    transform: translate(1px, 1px);
  }

  @keyframes ptt-glow {
    0% {
      box-shadow: 0 0 4px #ef4444;
    }
    100% {
      box-shadow: 0 0 14px #ef4444;
    }
  }

  .haptic-pulse-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #c084fc;
    display: inline-block;
  }

  .haptic-pulse-dot.vibrating {
    animation: vibrate-anim 0.2s infinite;
    background: #f43f5e;
  }

  @keyframes vibrate-anim {
    0%,
    100% {
      transform: translate(0, 0);
    }
    25% {
      transform: translate(-2px, 2px);
    }
    50% {
      transform: translate(2px, -2px);
    }
    75% {
      transform: translate(-2px, -2px);
    }
  }
`;
