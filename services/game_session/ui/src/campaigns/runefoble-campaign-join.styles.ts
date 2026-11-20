import { css, type CSSResult } from 'lit';
import { baseStyles } from './styles/base.styles.ts';

const joinLocalStyles = css`
  :host { display: block; }

  .join-card {
    background: var(--rf-bg-surface-elevated, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 6px 6px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    font-family: var(--rf-font-family, sans-serif);
    max-width: 480px; margin: 32px auto; padding: 24px;
  }

  .join-title { margin: 0 0 12px; font-size: 1.4rem; }
  .join-text { margin: 0 0 16px; color: var(--rf-text-secondary, rgb(60, 60, 60)); line-height: 1.5; }

  .join-form { display: flex; flex-direction: column; gap: 12px; }
  .join-label { display: flex; flex-direction: column; gap: 4px; font-weight: 700; }
  .join-input {
    font: inherit; padding: 8px 10px;
    background: var(--rf-bg-inset, rgb(245, 245, 245));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .join-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; }

  .join-button {
    font: inherit; font-weight: 700; padding: 10px 16px; cursor: pointer;
    background: var(--rf-accent-primary, rgb(220, 60, 40));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
  }
  .join-button:disabled { opacity: 0.6; cursor: wait; }

  .join-button-secondary {
    font: inherit; padding: 10px 16px; cursor: pointer;
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
  }

  .join-link {
    display: inline-block; font-weight: 700; padding: 10px 16px;
    background: var(--rf-accent-secondary, rgb(40, 110, 200));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    text-decoration: none;
  }

  .join-alert {
    margin: 0 0 12px; padding: 10px 12px;
    background: var(--rf-bg-inset, rgb(245, 245, 245));
    border: var(--rf-border-width, 2px) solid var(--rf-accent-primary, rgb(220, 60, 40));
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }
`;

export const campaignJoinStyles: CSSResult[] = [baseStyles, joinLocalStyles];
