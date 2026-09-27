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

  .campaign-detail-layout {
    display: flex;
    flex-direction: column;
    gap: 24px;
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
