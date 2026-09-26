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
`;
