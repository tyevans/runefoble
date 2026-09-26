import { css } from 'lit';

export const settingsModalLayoutStyles = css`
  :host {
    display: contents;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary);
  }

  .modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    width: 100vw; height: 100vh;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    padding: 16px;
    box-sizing: border-box;
    animation: rf-fade-in 0.15s ease-out;
  }
  @keyframes rf-fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .modal-dialog {
    background: var(--rf-bg-surface-elevated, var(--rf-bg-surface));
    color: var(--rf-text-primary);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    box-shadow: var(--rf-shadow);
    width: 100%;
    max-width: 640px; max-height: 90vh;
    display: flex; flex-direction: column;
    overflow: hidden;
    animation: rf-slide-up 0.18s ease-out;
  }
  @keyframes rf-slide-up {
    from { transform: translateY(12px); opacity: 0.8; }
    to { transform: translateY(0); opacity: 1; }
  }

  .modal-header {
    display: flex;
    align-items: center; justify-content: space-between;
    padding: 16px 20px;
    background: var(--rf-bg-canvas);
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
  }
  .modal-title-group {
    display: flex; align-items: center; gap: 10px;
  }
  .modal-icon-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 30px; height: 30px;
    background: var(--rf-accent-tertiary);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    font-size: 0.95rem;
  }
  .modal-title {
    margin: 0;
    font-size: 1.25rem; font-weight: 900; letter-spacing: -0.02em;
  }

  .close-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 32px; height: 32px;
    background: var(--rf-bg-surface);
    color: var(--rf-text-primary);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm);
    font-size: 1rem; font-weight: 800; cursor: pointer;
    transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.1s ease;
  }
  .close-btn:hover {
    background: var(--rf-accent-primary); color: var(--rf-text-inverse);
    transform: translate(-1px, -1px); box-shadow: var(--rf-shadow);
  }
  .close-btn:active {
    transform: translate(1px, 1px); box-shadow: none;
  }

  .modal-body {
    padding: 20px;
    overflow-y: auto; flex: 1;
    display: flex; flex-direction: column; gap: 24px;
  }

  .modal-footer {
    display: flex;
    align-items: center; justify-content: space-between;
    padding: 14px 20px;
    background: var(--rf-bg-canvas);
    border-top: var(--rf-border-width, 2px) solid var(--rf-border-color);
  }
  .status-text {
    font-size: 0.75rem; color: var(--rf-text-muted); font-weight: 600;
  }
  .done-btn {
    padding: 8px 18px;
    font-size: 0.85rem; font-weight: 800;
    background: var(--rf-accent-tertiary);
    color: var(--rf-text-primary);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm);
    cursor: pointer;
    transition: all 0.12s ease;
  }
  .done-btn:hover {
    transform: translate(-1px, -1px); box-shadow: var(--rf-shadow);
  }
  .done-btn:active {
    transform: translate(1px, 1px); box-shadow: none;
  }

  @media (max-width: 640px) {
    .modal-overlay { padding: 0; }
    .modal-dialog {
      max-height: 100vh; height: 100vh;
      border-radius: 0; border: none;
    }
  }
`;

export const layoutStyles = settingsModalLayoutStyles;
