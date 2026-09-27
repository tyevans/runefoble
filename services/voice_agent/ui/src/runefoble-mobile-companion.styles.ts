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
    font-size: 1.1rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .badge-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .badge {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 3px 8px;
    border: 1px solid var(--rf-border-color, #111111);
    border-radius: 2px;
    text-transform: uppercase;
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
    font-size: 0.85rem;
  }

  .status-label {
    font-weight: 600;
    color: var(--rf-text-muted, #4b5563);
  }

  .status-value {
    font-family: monospace;
    font-weight: 700;
  }

  .whisper-card {
    background: #1e1b4b;
    color: #e0e7ff;
    border: 2px solid #818cf8;
    border-radius: 4px;
    padding: 14px;
    box-shadow: 0 0 12px rgba(129, 140, 248, 0.4);
    animation: whisper-glow 2s infinite alternate;
  }

  @keyframes whisper-glow {
    0% { border-color: #818cf8; box-shadow: 0 0 8px rgba(129, 140, 248, 0.3); }
    100% { border-color: #c084fc; box-shadow: 0 0 16px rgba(192, 132, 252, 0.6); }
  }

  .whisper-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 800;
    font-size: 0.85rem;
    text-transform: uppercase;
    color: #a5b4fc;
    margin-bottom: 6px;
  }

  .whisper-body {
    font-style: italic;
    font-size: 0.95rem;
    line-height: 1.4;
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
    0% { transform: scale(1); }
    100% { transform: scale(1.01); }
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
    transition: transform 0.1s ease;
  }

  .btn:active {
    transform: translate(1px, 1px);
  }

  .btn-ptt {
    background: #3b82f6;
    color: #ffffff;
    font-size: 1rem;
    padding: 12px;
    text-align: center;
    text-transform: uppercase;
    font-weight: 800;
  }

  .btn-ptt.active {
    background: #ef4444;
  }

  .haptic-pulse-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #c084fc;
    display: inline-block;
  }

  .haptic-pulse-dot.vibrating {
    animation: vibrate-anim 0.2s infinite;
  }

  @keyframes vibrate-anim {
    0%, 100% { transform: translate(0, 0); }
    25% { transform: translate(-2px, 2px); }
    50% { transform: translate(2px, -2px); }
    75% { transform: translate(-2px, -2px); }
  }
`;
