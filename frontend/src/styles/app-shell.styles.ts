import { css } from 'lit';

export const appShellStyles = css`
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

  .character-column {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .voice-container {
    margin-top: 24px;
  }

  .campaign-hub-layout {
    display: flex;
    flex-direction: column;
    gap: 20px;
    max-width: 1400px;
    margin: 0 auto;
    width: 100%;
  }

  .campaign-nav-tabs {
    display: flex;
    gap: 8px;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
    padding-bottom: 0;
    margin-top: 8px;
    margin-bottom: 12px;
    overflow-x: auto;
  }

  .campaign-nav-tabs .nav-tab {
    display: inline-flex;
    align-items: center;
    padding: 10px 18px;
    font-size: 0.95rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--rf-text-muted);
    background: transparent;
    border: var(--rf-border-width, 2px) solid transparent;
    border-bottom: none;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.15s ease-in-out;
    position: relative;
    bottom: -2px;
    border-radius: var(--rf-border-radius, 0px) var(--rf-border-radius, 0px) 0 0;
  }

  .campaign-nav-tabs .nav-tab:hover {
    color: var(--rf-text-primary);
    background: var(--rf-bg-surface);
  }

  .campaign-nav-tabs .nav-tab.active {
    color: var(--rf-accent-primary);
    background: var(--rf-bg-surface);
    border-color: var(--rf-border-color);
    border-bottom: 2px solid var(--rf-bg-surface);
    font-weight: 800;
  }

  .campaign-tab-content {
    min-height: 300px;
  }

  .campaign-detail-layout {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .profile-layout {
    padding: 32px;
    background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow);
    max-width: 600px;
    margin: 24px auto;
  }

  .auth-fallback-view {
    padding: 48px;
    text-align: center;
    background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow);
    max-width: 600px;
    margin: 40px auto;
  }

  .auth-fallback-view h2 {
    font-size: 1.5rem;
    margin-top: 0;
    margin-bottom: 12px;
    color: var(--rf-text-primary);
  }

  .auth-fallback-view p {
    color: var(--rf-text-muted);
    margin-bottom: 24px;
  }
`;
