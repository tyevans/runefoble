import { css } from 'lit';

export const viewportStyles = css`
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

  .device-icon { font-size: 1.25rem; }

  .title-text {
    font-weight: 800;
    font-size: 1.05rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
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
    border: 2px solid var(--rf-border-color, #111111);
    touch-action: none;
    box-shadow: 3px 3px 0px rgba(0, 0, 0, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    cursor: pointer;
  }

  .btn-ptt:hover { background: #1d4ed8; }

  .btn-ptt.active {
    background: #dc2626;
    animation: ptt-glow 0.8s infinite alternate;
    box-shadow: inset 2px 2px 4px rgba(0, 0, 0, 0.4);
    transform: translate(1px, 1px);
  }

  @keyframes ptt-glow {
    0% { box-shadow: 0 0 4px #ef4444; }
    100% { box-shadow: 0 0 14px #ef4444; }
  }
`;
