import { css } from 'lit';

export const sessionLobbyStyles = css`
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

  /* Participant Roster Cards */
  .participants-section {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .section-label {
    font-size: 0.85rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--rf-text-secondary, rgb(43, 45, 66));
  }
  .participants-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 18px;
  }
  .participant-card {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 4px 4px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .participant-card.current-user {
    border-color: var(--rf-border-focus, rgb(29, 53, 87));
    outline: 2px dashed var(--rf-border-focus, rgb(29, 53, 87));
    outline-offset: 2px;
  }
  .participant-card.absent {
    opacity: 0.85;
    background: var(--rf-bg-inset, rgb(241, 243, 245));
  }

  /* Card Header: Avatar, Name, Online Status, Role */
  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }
  .user-identity {
    display: flex;
    align-items: center;
    gap: 12px;
    overflow: hidden;
  }
  .avatar-wrap {
    position: relative;
    width: 44px;
    height: 44px;
    flex-shrink: 0;
  }
  .avatar-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
  }
  .avatar-fallback {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--rf-accent-secondary, rgb(29, 53, 87));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    font-weight: 900;
    font-size: 1.1rem;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
  }
  .presence-dot {
    position: absolute;
    bottom: -2px;
    right: -2px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid var(--rf-bg-surface, rgb(255, 255, 255));
  }
  .presence-dot.online { background: rgb(34, 197, 94); }
  .presence-dot.idle { background: var(--rf-accent-tertiary, rgb(255, 183, 3)); }
  .presence-dot.offline { background: rgb(156, 163, 175); }

  .user-info {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .username {
    font-weight: 800;
    font-size: 1rem;
    color: var(--rf-text-primary, rgb(18, 18, 18));
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .user-role {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--rf-text-muted, rgb(100, 116, 139));
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  /* Readiness Badges */
  .badge-readiness {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 4px 8px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    white-space: nowrap;
  }
  .badge-ready {
    background: rgb(34, 197, 94);
    color: rgb(255, 255, 255);
  }
  .badge-setting-up {
    background: var(--rf-accent-tertiary, rgb(255, 183, 3));
    color: rgb(18, 18, 18);
  }
  .badge-standin {
    background: rgb(168, 85, 247);
    color: rgb(255, 255, 255);
  }

  /* Character Preview Box */
  .character-card-preview {
    background: var(--rf-bg-inset, rgb(241, 243, 245));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .char-portrait,
  .char-portrait-fallback {
    width: 36px;
    height: 36px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    flex-shrink: 0;
  }
  .char-portrait { object-fit: cover; }
  .char-portrait-fallback {
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 0.9rem;
    color: var(--rf-text-muted, rgb(100, 116, 139));
  }
  .char-details {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .char-name {
    font-weight: 800;
    font-size: 0.9rem;
    color: var(--rf-text-primary, rgb(18, 18, 18));
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .char-meta {
    font-size: 0.75rem;
    color: var(--rf-text-secondary, rgb(43, 45, 66));
    font-weight: 600;
  }
  .no-character-msg {
    font-size: 0.8rem;
    font-style: italic;
    color: var(--rf-text-muted, rgb(100, 116, 139));
  }

  /* Character Selector Dropdown */
  .char-select-container {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .select-label {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--rf-text-secondary, rgb(43, 45, 66));
  }
  .character-dropdown {
    width: 100%;
    padding: 8px 10px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    font-family: inherit;
    font-size: 0.85rem;
    font-weight: 700;
    cursor: pointer;
  }
  .character-dropdown:focus {
    outline: none;
    border-color: var(--rf-border-focus, rgb(29, 53, 87));
  }

  /* Participant Controls / Checkboxes */
  .card-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--rf-border-subtle, rgba(18, 18, 18, 0.15));
  }
  .control-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.82rem;
    font-weight: 700;
    cursor: pointer;
    color: var(--rf-text-primary, rgb(18, 18, 18));
    user-select: none;
  }
  .control-toggle input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--rf-accent-primary, rgb(230, 57, 70));
    cursor: pointer;
  }

  /* Empty State */
  .empty-state {
    padding: 40px 24px;
    text-align: center;
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 4px 4px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
  }
  .empty-state h3 {
    margin: 0 0 8px 0;
    font-size: 1.2rem;
    font-weight: 800;
  }
  .empty-state p {
    margin: 0;
    color: var(--rf-text-muted, rgb(100, 116, 139));
    font-size: 0.9rem;
  }

  @media (max-width: 640px) {
    .lobby-header {
      flex-direction: column;
      align-items: flex-start;
    }
    .header-actions {
      width: 100%;
      flex-direction: column;
      align-items: stretch;
    }
    .btn-launch {
      width: 100%;
      justify-content: center;
    }
  }
`;
