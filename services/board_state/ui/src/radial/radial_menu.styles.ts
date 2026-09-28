import { css } from 'lit';

export const radialMenuStyles = css`
  :host {
    position: absolute; top: 0; left: 0; z-index: 1000;
    pointer-events: auto; user-select: none; -webkit-user-select: none;
  }
  .radial-container {
    position: relative; width: 0; height: 0;
    animation: bloom 120ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
  @keyframes bloom {
    from { transform: scale(0.2) rotate(-20deg); opacity: 0; }
    to { transform: scale(1) rotate(0deg); opacity: 1; }
  }
  .backdrop {
    position: fixed; inset: 0; z-index: -1;
    background: rgba(0, 0, 0, 0.25); cursor: default;
  }
  .center-button {
    position: absolute; top: -20px; left: -20px;
    width: 40px; height: 40px; border-radius: 50%;
    background: var(--rf-bg-surface-elevated, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: 2px solid var(--rf-border-color, #121212);
    box-shadow: 2px 2px 0px var(--rf-shadow-color, #121212);
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 800; cursor: pointer; z-index: 2;
    transition: transform 0.1s ease, background 0.1s ease;
  }
  .center-button:hover, .center-button:active {
    transform: scale(1.08); background: var(--rf-accent-primary, #e63946); color: #ffffff;
  }
  .action-wedge {
    position: absolute; width: 46px; height: 46px;
    margin-top: -23px; margin-left: -23px; border-radius: 50%;
    border: 2px solid var(--rf-border-color, #121212);
    box-shadow: 3px 3px 0px var(--rf-shadow-color, #121212);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    cursor: pointer; color: #ffffff; touch-action: none;
    transition: transform 0.12s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.12s ease;
  }
  .action-wedge:hover, .action-wedge.active {
    transform: scale(1.18); box-shadow: 4px 4px 0px var(--rf-shadow-color, #121212);
  }
  .glyph {
    width: 22px; height: 22px;
    filter: drop-shadow(1px 1px 0px rgba(0, 0, 0, 0.4));
  }
  .action-label {
    position: absolute; bottom: -18px;
    font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;
    background: var(--rf-bg-surface-elevated, #ffffff);
    color: var(--rf-text-primary, #121212);
    padding: 1px 4px; border: 1px solid var(--rf-border-color, #121212);
    border-radius: 2px; white-space: nowrap; pointer-events: none;
    box-shadow: 1px 1px 0px var(--rf-shadow-color, #121212);
  }
  .tooltip {
    position: absolute; top: 56px; left: -90px; width: 180px;
    background: var(--rf-bg-surface-elevated, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: 2px solid var(--rf-border-color, #121212);
    box-shadow: 3px 3px 0px var(--rf-shadow-color, #121212);
    padding: 6px 10px; font-size: 11px; text-align: center;
    pointer-events: none; font-weight: 600;
  }
`;
