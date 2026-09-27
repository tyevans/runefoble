import { css } from 'lit';

export const badgeStyles = css`
  :host {
    display: inline-block;
  }

  .badge-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
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

  .badge.latency {
    background: #e2e8f0;
    color: #334155;
    font-family: monospace;
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

  .reconnect-btn {
    font-size: 0.68rem;
    padding: 2px 6px;
    cursor: pointer;
    background: #ffffff;
    border: 1px solid #111111;
  }
`;
