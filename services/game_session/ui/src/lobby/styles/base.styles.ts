import { css } from 'lit';

export const baseStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }
  * { box-sizing: border-box; }

  .lobby-container {
    display: flex;
    flex-direction: column;
    gap: 24px;
    width: 100%;
    max-width: 1100px;
    margin: 0 auto;
  }

  /* Header Section */
  .lobby-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
    padding-bottom: 20px;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
  }
  .header-titles {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .lobby-badge-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    width: fit-content;
    padding: 3px 10px;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: var(--rf-bg-inset, rgb(241, 243, 245));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }
  .status-pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--rf-accent-tertiary, rgb(255, 183, 3));
    display: inline-block;
  }
  .lobby-title {
    font-size: 1.75rem;
    font-weight: 900;
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }
  .lobby-subtitle {
    font-size: 0.9rem;
    color: var(--rf-text-muted, rgb(100, 116, 139));
    margin: 0;
    font-weight: 600;
  }

  /* DM Controls and Summary Bar */
  .header-actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 14px;
  }
  .readiness-summary-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    background: var(--rf-bg-surface-elevated, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    font-weight: 800;
    font-size: 0.85rem;
    color: var(--rf-text-primary, rgb(18, 18, 18));
    letter-spacing: 0.02em;
  }
  .btn-launch {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 4px 4px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 10px 22px;
    font-weight: 900;
    font-size: 0.95rem;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .btn-launch:hover:not(:disabled) {
    transform: translate(-2px, -2px);
    box-shadow: 6px 6px 0px var(--rf-shadow-color, rgb(18, 18, 18));
  }
  .btn-launch:active:not(:disabled) {
    transform: translate(1px, 1px);
    box-shadow: 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18));
  }
  .btn-launch:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    filter: grayscale(0.4);
  }

  @media (max-width: 640px) {
    .lobby-header { flex-direction: column; align-items: flex-start; }
    .header-actions { width: 100%; flex-direction: column; align-items: stretch; }
    .btn-launch { width: 100%; justify-content: center; }
  }
`;
