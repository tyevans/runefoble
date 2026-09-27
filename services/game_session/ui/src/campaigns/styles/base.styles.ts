import { css } from 'lit';

export const baseStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  * {
    box-sizing: border-box;
  }

  .members-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .members-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding-bottom: 16px;
  }

  .header-left {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .members-title {
    font-size: 1.4rem;
    font-weight: 900;
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .members-subtitle {
    font-size: 0.85rem;
    color: var(--rf-text-muted, rgb(100, 116, 139));
    margin: 0;
    font-weight: 600;
  }

  .header-actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .btn-invite {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 8px 16px;
    font-weight: 800;
    font-size: 0.85rem;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .btn-invite:hover {
    transform: translate(-1px, -1px);
    box-shadow: 3px 3px 0px var(--rf-shadow-color, rgb(18, 18, 18));
  }
`;
