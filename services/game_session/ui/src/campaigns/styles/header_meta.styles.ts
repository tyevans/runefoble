import { css } from 'lit';

export const headerMetaStyles = css`
  /* Header Content */
  .header-content {
    padding: 20px 24px 24px 24px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  /* Badges Row */
  .meta-badges-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border: 1.5px solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: 1px 1px 0px var(--rf-shadow-color, rgb(18, 18, 18));
    line-height: 1.2;
  }

  .badge-system {
    background: var(--rf-accent-secondary, rgb(29, 53, 87));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
  }

  .badge-setting {
    background: var(--rf-accent-tertiary, rgb(255, 183, 3));
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .badge-status {
    background: var(--rf-bg-inset, rgb(241, 250, 238));
    color: var(--rf-text-secondary, rgb(45, 55, 72));
  }

  .badge-status.status-active {
    background: rgba(42, 157, 143, 0.15);
    border-color: var(--rf-accent-success, rgb(42, 157, 143));
    color: var(--rf-accent-success, rgb(42, 157, 143));
  }

  .status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: currentColor;
    display: inline-block;
  }

  .badge-dm-profile {
    background: var(--rf-bg-inset, rgb(241, 250, 238));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 8px 3px 4px;
    border: 1.5px solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: 1px 1px 0px var(--rf-shadow-color, rgb(18, 18, 18));
    font-size: 0.75rem;
    font-weight: 700;
  }

  .dm-avatar {
    width: 20px; height: 20px;
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 0.7rem;
    border: 1px solid var(--rf-border-color, rgb(18, 18, 18));
  }

  .dm-name {
    font-weight: 800;
  }

  .dm-role-tag {
    font-size: 0.65rem;
    color: var(--rf-text-muted, rgb(100, 116, 139));
    text-transform: uppercase;
  }

  /* Title Typography */
  .campaign-title {
    font-size: 1.85rem;
    font-weight: 900;
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    color: var(--rf-text-primary, rgb(18, 18, 18));
    line-height: 1.2;
    flex: 1;
    min-width: 240px;
  }

  /* Narrative Description */
  .campaign-description {
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--rf-text-secondary, rgb(45, 55, 72));
    border-left: 3px solid var(--rf-accent-secondary, rgb(29, 53, 87));
    padding-left: 14px;
    margin: 0;
  }

  .campaign-description p {
    margin: 0;
  }

  .campaign-description-empty {
    font-style: italic;
    color: var(--rf-text-muted, rgb(100, 116, 139));
  }
`;
