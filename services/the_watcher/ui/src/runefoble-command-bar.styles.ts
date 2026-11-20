import { css } from 'lit';

/** Styles of `<runefoble-command-bar>`. Bauhaus tokens only (docs/reference/design-tokens-and-themes.md). */
export const commandBarStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary);
    background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow);
    padding: 12px;
    box-sizing: border-box;
    width: 100%;
  }

  .bar {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .label {
    font-weight: 900;
    text-transform: uppercase;
    font-size: 0.8rem;
    letter-spacing: 0.04em;
  }

  .input {
    flex: 1;
    min-width: 0;
    padding: 8px 10px;
    font: inherit;
    color: var(--rf-text-primary);
    background: var(--rf-bg-inset, var(--rf-bg-canvas));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
  }

  .input:disabled {
    color: var(--rf-text-muted);
    cursor: not-allowed;
  }

  .send {
    padding: 8px 16px;
    font: inherit;
    font-weight: 900;
    text-transform: uppercase;
    color: var(--rf-text-inverse);
    background: var(--rf-accent-secondary);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: 3px 3px 0 var(--rf-shadow-color);
    cursor: pointer;
  }

  .send:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    box-shadow: none;
  }

  .status {
    margin: 8px 0 0;
    font-size: 0.9rem;
  }

  .status.notice,
  .status.sending {
    color: var(--rf-text-muted);
  }

  .status.reply {
    border-left: 4px solid var(--rf-accent-tertiary);
    padding-left: 8px;
  }

  .status.error {
    color: var(--rf-accent-primary);
    font-weight: 700;
  }
`;
