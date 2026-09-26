import { css } from 'lit';

export const runefobleAppStyles = css`
  :host {
    display: block;
    min-height: 100vh;
    background-color: var(--rf-bg-canvas);
    color: var(--rf-text-primary);
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    padding: 24px;
    box-sizing: border-box;
    transition: background-color 0.2s ease, color 0.2s ease;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 20px;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 16px;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .brand h1 {
    font-size: 1.9rem;
    margin: 0;
    color: var(--rf-text-primary);
    font-weight: 900;
    letter-spacing: -0.5px;
  }
  .tagline {
    font-size: 0.9rem;
    color: var(--rf-text-muted);
  }
  .header-actions {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }
  .settings-trigger {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--rf-bg-surface);
    color: var(--rf-text-primary);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm);
    font-weight: 700;
    font-size: 0.8rem;
    padding: 4px 10px;
    cursor: pointer;
    border-radius: var(--rf-border-radius, 0px);
    transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.1s ease;
  }
  .settings-trigger:hover {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow);
  }
  .settings-trigger:active {
    transform: translate(1px, 1px);
    box-shadow: none;
  }
  .view-mode-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--rf-bg-surface);
    color: var(--rf-text-primary);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm);
    border-radius: var(--rf-border-radius, 0px);
    font-weight: 700;
    font-size: 0.8rem;
    padding: 4px 10px;
    cursor: pointer;
    transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.1s ease;
  }
  .view-mode-btn:hover {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow);
  }
  .view-mode-btn:active {
    transform: translate(1px, 1px);
    box-shadow: none;
  }
  @media (max-width: 640px) {
    .settings-label {
      display: none;
    }
  }
  .session-info {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.85rem;
  }
  .badge-live {
    background: var(--rf-bg-surface);
    color: var(--rf-accent-primary);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    box-shadow: var(--rf-shadow-sm);
    padding: 4px 12px;
    font-weight: 700;
  }
  .badge-socket {
    font-size: 0.75rem;
    padding: 4px 10px;
    border-radius: var(--rf-border-radius, 0px);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    background: var(--rf-bg-surface);
    font-weight: 700;
    box-shadow: var(--rf-shadow-sm);
  }
  .badge-socket.connected {
    color: var(--rf-accent-secondary);
  }
  .badge-socket.disconnected {
    color: var(--rf-accent-primary);
  }
  .layout-grid {
    display: grid;
    grid-template-columns: 1fr 340px 420px;
    gap: 24px;
    align-items: start;
  }
  @media (max-width: 1280px) {
    .layout-grid {
      grid-template-columns: 1fr;
    }
  }
`;
