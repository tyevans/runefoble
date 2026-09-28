import { css } from 'lit';

export const campaignHeaderStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  * {
    box-sizing: border-box;
  }

  .campaign-header-card {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 4px 4px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    overflow: hidden;
    position: relative;
  }

  /* Hero Banner */
  .hero-banner {
    position: relative;
    width: 100%;
    min-height: 160px;
    max-height: 260px;
    overflow: hidden;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-surface-elevated, rgb(240, 240, 240));
  }

  .cover-image {
    width: 100%;
    height: 220px;
    object-fit: cover;
    display: block;
  }

  /* Bauhaus Fallback Pattern */
  .hero-banner-fallback {
    width: 100%;
    height: 180px;
    background: linear-gradient(
      135deg,
      var(--rf-accent-secondary, rgb(29, 53, 87)) 0%,
      var(--rf-accent-primary, rgb(230, 57, 70)) 65%,
      var(--rf-accent-tertiary, rgb(255, 183, 3)) 100%
    );
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .geometric-pattern {
    position: absolute;
    inset: 0;
    opacity: 0.25;
    background-image:
      linear-gradient(var(--rf-border-color, rgb(18, 18, 18)) 2px, transparent 2px),
      linear-gradient(90deg, var(--rf-border-color, rgb(18, 18, 18)) 2px, transparent 2px);
    background-size: 32px 32px;
  }

  .geometric-accent-circle {
    position: absolute;
    width: 140px;
    height: 140px;
    border-radius: 50%;
    border: 3px solid var(--rf-text-inverse, rgb(255, 255, 255));
    top: -20px;
    right: 40px;
    opacity: 0.4;
  }

  .geometric-accent-bar {
    position: absolute;
    width: 180px;
    height: 14px;
    background: var(--rf-accent-tertiary, rgb(255, 183, 3));
    bottom: 24px;
    left: -20px;
    transform: rotate(-12deg);
    border: 2px solid var(--rf-border-color, rgb(18, 18, 18));
  }

  .fallback-hero-title {
    position: relative;
    z-index: 1;
    font-size: 1.6rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    text-shadow: 2px 2px 0px var(--rf-border-color, rgb(18, 18, 18));
    padding: 0 16px;
    text-align: center;
  }

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
    width: 7px;
    height: 7px;
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
    width: 20px;
    height: 20px;
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

  /* Title & Action Row */
  .title-action-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    flex-wrap: wrap;
  }

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

  .btn-edit-campaign {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 7px 16px;
    font-weight: 800;
    font-size: 0.82rem;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
    white-space: nowrap;
  }

  .btn-edit-campaign:hover {
    transform: translate(-1px, -1px);
    box-shadow: 3px 3px 0px var(--rf-shadow-color, rgb(18, 18, 18));
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

  /* Modal Dialog */
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: var(--rf-z-modal, 1000);
    padding: 16px;
  }

  .modal-card {
    background: var(--rf-bg-surface-elevated, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 6px 6px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    width: 100%;
    max-width: 520px;
    padding: 24px;
    max-height: 90vh;
    overflow-y: auto;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding-bottom: 12px;
    margin-bottom: 20px;
  }

  .modal-title {
    font-size: 1.25rem;
    font-weight: 900;
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .btn-close {
    background: transparent;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    width: 32px;
    height: 32px;
    font-weight: 900;
    font-size: 1.1rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--rf-text-primary, rgb(18, 18, 18));
    transition: transform 0.1s ease, background 0.1s ease;
  }

  .btn-close:hover {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    transform: translate(-1px, -1px);
  }

  .form-group {
    margin-bottom: 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .form-label {
    font-size: 0.8rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--rf-text-primary, rgb(18, 18, 18));
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .required-star {
    color: var(--rf-accent-primary, rgb(230, 57, 70));
  }

  .form-input,
  .form-select,
  .form-textarea {
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding: 10px 12px;
    background: var(--rf-bg-inset, rgb(248, 249, 250));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: 600;
    width: 100%;
    outline: none;
    transition: border-color 0.15s ease;
  }

  .form-input:focus,
  .form-select:focus,
  .form-textarea:focus {
    border-color: var(--rf-border-focus, rgb(255, 183, 3));
  }

  .form-textarea {
    min-height: 80px;
    resize: vertical;
  }

  .error-banner {
    background: rgba(230, 57, 70, 0.12);
    border: var(--rf-border-width, 2px) solid var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-accent-primary, rgb(230, 57, 70));
    padding: 10px 14px;
    font-weight: 800;
    font-size: 0.85rem;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
    border-top: 1px solid var(--rf-border-subtle, rgba(18, 18, 18, 0.15));
    padding-top: 18px;
  }

  .btn-cancel {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 9px 18px;
    font-weight: 800;
    font-size: 0.9rem;
    cursor: pointer;
    color: var(--rf-text-primary, rgb(18, 18, 18));
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .btn-cancel:hover {
    background: var(--rf-bg-inset, rgb(241, 250, 238));
  }

  .btn-submit {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 9px 22px;
    font-weight: 900;
    font-size: 0.9rem;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }

  .btn-submit:hover:not(:disabled) {
    transform: translate(-1px, -1px);
    box-shadow: 3px 3px 0px var(--rf-shadow-color, rgb(18, 18, 18));
  }

  .btn-submit:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;
