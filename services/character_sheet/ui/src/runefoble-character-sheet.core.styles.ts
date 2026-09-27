import { css } from 'lit';

export const characterSheetCoreStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    background: var(--rf-bg-card, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    border-radius: var(--rf-border-radius, 0px);
    padding: 20px;
    color: var(--rf-text-primary, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px var(--rf-shadow-color, #121212));
    box-sizing: border-box;
    width: 100%;
    max-width: 860px;
  }

  .sheet-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 12px;
    margin-bottom: 16px;
    gap: 12px;
  }

  .char-identity h1 {
    font-size: 1.5rem;
    font-weight: 800;
    margin: 0 0 4px 0;
    letter-spacing: -0.02em;
  }

  .char-meta {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--rf-text-muted, #4b5563);
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .badge-stand-in {
    background: var(--rf-accent-tertiary, #ffb703);
    color: var(--rf-color-dark, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    font-size: 0.75rem;
    font-weight: 800;
    padding: 2px 8px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    text-transform: uppercase;
  }

  /* Core Stats Row */
  .vitals-grid {
    display: grid;
    grid-template-columns: 2fr repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 18px;
  }

  .vital-card {
    background: var(--rf-bg-canvas, #f8f9fa);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 8px 12px;
    text-align: center;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
  }

  .vital-label {
    font-size: 0.7rem;
    font-weight: 800;
    text-transform: uppercase;
    color: var(--rf-text-muted, #4b5563);
    margin-bottom: 2px;
  }

  .vital-val {
    font-size: 1.25rem;
    font-weight: 800;
  }

  .hp-bar-outer {
    height: 10px;
    background: var(--rf-bg-surface, #ffffff);
    border: 1px solid var(--rf-border-color, #121212);
    margin-top: 4px;
    overflow: hidden;
  }

  .hp-bar-inner {
    height: 100%;
    background: var(--rf-accent-secondary, #1d3557);
    transition: width 0.3s ease;
  }

  .hp-bar-inner.low {
    background: var(--rf-accent-primary, #e63946);
  }

  /* Two Column Main Content */
  .columns-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 18px;
  }

  .section-panel {
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 14px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    box-sizing: border-box;
  }

  .section-title {
    font-size: 0.9rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 12px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--rf-border-subtle, #d1d5db);
    padding-bottom: 6px;
  }
`;

export const coreStyles = characterSheetCoreStyles;
