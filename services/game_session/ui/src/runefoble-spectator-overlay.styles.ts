import { css } from 'lit';

export const spectatorOverlayStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #ffffff);
    pointer-events: none;
    width: 100%;
    user-select: none;
  }

  :host([transparent-mode]) {
    background: transparent !important;
    background-color: rgba(0, 0, 0, 0) !important;
    box-shadow: none !important;
  }

  /* Overlay Layout Container */
  .overlay-container {
    display: flex;
    gap: 16px;
    width: 100%;
    box-sizing: border-box;
    pointer-events: none;
  }

  .overlay-container.bottom {
    flex-direction: row;
    justify-content: flex-start;
    align-items: flex-end;
    flex-wrap: wrap;
    padding: 16px 24px;
  }

  .overlay-container.top {
    flex-direction: row;
    justify-content: flex-start;
    align-items: flex-start;
    flex-wrap: wrap;
    padding: 16px 24px;
  }

  .overlay-container.sidebar {
    flex-direction: column;
    justify-content: flex-start;
    align-items: flex-start;
    width: 280px;
    padding: 16px;
  }

  /* Party Member Vitals Card */
  .party-vitals-card {
    background: rgba(18, 18, 24, 0.9);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #3b82f6);
    box-shadow: var(--rf-shadow-sm, 3px 3px 0px rgba(0, 0, 0, 0.7));
    padding: 10px 14px;
    min-width: 200px;
    max-width: 260px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    pointer-events: auto;
    transition: transform 300ms cubic-bezier(0.25, 0.1, 0.25, 1);
  }

  .party-vitals-card.active-turn {
    border-color: var(--rf-accent-secondary, #f59e0b);
    box-shadow: 0 0 14px rgba(245, 158, 11, 0.75), 3px 3px 0px rgba(0, 0, 0, 0.8);
    transform: translateY(-4px);
  }

  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }

  .character-name {
    font-weight: 900;
    font-size: 0.95rem;
    letter-spacing: -0.2px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .avatar-badge {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    font-weight: 900;
    color: #fff;
    border: 1px solid var(--rf-border-color, #000);
  }

  .hp-counter {
    font-weight: 800;
    font-size: 0.82rem;
    color: var(--rf-text-muted, #94a3b8);
  }

  .hp-counter strong {
    color: var(--rf-text-primary, #ffffff);
  }

  /* HP Bar */
  .hp-bar-track {
    width: 100%;
    height: 10px;
    background: #1e293b;
    border: 1px solid #334155;
    position: relative;
    overflow: hidden;
  }

  .hp-bar-fill {
    height: 100%;
    transition: width 300ms cubic-bezier(0.25, 0.1, 0.25, 1), background-color 300ms ease;
  }

  .hp-bar-fill.healthy {
    background: #10b981;
  }

  .hp-bar-fill.wounded {
    background: #f59e0b;
  }

  .hp-bar-fill.critical {
    background: #ef4444;
    animation: criticalPulse 1s ease-in-out infinite alternate;
  }

  @keyframes criticalPulse {
    0% { opacity: 0.8; }
    100% { opacity: 1; }
  }

  /* Badges & Tags */
  .badges-row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: center;
  }

  .status-badge {
    background: var(--rf-color-red, #dc2626);
    color: #ffffff;
    font-size: 0.62rem;
    font-weight: 800;
    padding: 2px 6px;
    border: 1px solid rgba(0, 0, 0, 0.4);
    text-transform: uppercase;
  }

  .ai-tag {
    background: var(--rf-color-yellow, #f59e0b);
    color: #000000;
    font-size: 0.62rem;
    font-weight: 900;
    padding: 2px 5px;
    border: 1px solid rgba(0, 0, 0, 0.4);
  }

  .turn-tag {
    background: var(--rf-accent-secondary, #3b82f6);
    color: #ffffff;
    font-size: 0.62rem;
    font-weight: 900;
    padding: 2px 6px;
    animation: flashTurn 1.5s ease-in-out infinite alternate;
  }

  @keyframes flashTurn {
    0% { opacity: 0.85; }
    100% { opacity: 1; filter: drop-shadow(0 0 4px #60a5fa); }
  }

  /* Animated Dice Roll Overlay Banner */
  .roll-banner-container {
    position: fixed;
    top: 36px;
    left: 50%;
    transform: translateX(-50%);
    pointer-events: none;
    z-index: 9999;
  }

  .roll-banner {
    background: rgba(15, 23, 42, 0.95);
    border: var(--rf-border-width, 3px) solid var(--rf-border-color, #3b82f6);
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.6), 5px 5px 0px rgba(0, 0, 0, 0.8);
    padding: 14px 28px;
    display: flex;
    align-items: center;
    gap: 16px;
    animation: rollPop 300ms cubic-bezier(0.25, 0.1, 0.25, 1);
  }

  .roll-banner.crit {
    border-color: #f59e0b;
    box-shadow: 0 0 28px rgba(245, 158, 11, 0.9), 5px 5px 0px rgba(0, 0, 0, 0.8);
  }

  .roll-banner.fumble {
    border-color: #ef4444;
    box-shadow: 0 0 28px rgba(239, 68, 68, 0.9), 5px 5px 0px rgba(0, 0, 0, 0.8);
  }

  @keyframes rollPop {
    0% { transform: scale(0.7) translateY(-20px); opacity: 0; }
    100% { transform: scale(1) translateY(0); opacity: 1; }
  }

  .roll-roller {
    font-weight: 800;
    font-size: 1.1rem;
    color: #93c5fd;
  }

  .roll-formula {
    font-size: 0.85rem;
    color: #94a3b8;
  }

  .roll-result {
    font-weight: 900;
    font-size: 1.8rem;
    background: var(--rf-color-yellow, #f59e0b);
    color: #000000;
    padding: 2px 12px;
    border: 2px solid #000;
  }

  /* Camera Director Viewport HUD */
  .camera-hud-badge {
    position: fixed;
    top: 14px;
    right: 20px;
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.2);
    font-size: 0.7rem;
    padding: 4px 8px;
    display: flex;
    align-items: center;
    gap: 6px;
    color: #94a3b8;
  }

  .camera-indicator-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #ef4444;
    animation: liveCam 1.2s infinite;
  }

  @keyframes liveCam {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
`;
