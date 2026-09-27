import { css } from 'lit';

export const rosterStyles = css`
  /* Roster Table / List */
  .roster-card {
    background: var(--rf-bg-surface-elevated, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 6px 6px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    overflow: hidden;
  }

  .roster-list {
    display: flex;
    flex-direction: column;
    divide-y: 1px solid var(--rf-border-subtle, rgba(18, 18, 18, 0.15));
  }

  .member-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 18px;
    gap: 16px;
    border-bottom: 1px solid var(--rf-border-subtle, rgba(18, 18, 18, 0.12));
    transition: background 0.15s ease;
  }

  .member-item:last-child {
    border-bottom: none;
  }

  .member-item:hover {
    background: var(--rf-bg-inset, rgb(248, 249, 250));
  }

  .member-profile {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }

  .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-accent-secondary, rgb(29, 53, 87));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    display: flex; align-items: center; justify-content: center;
    font-weight: 900; font-size: 0.95rem;
    flex-shrink: 0; overflow: hidden;
  }

  .avatar img {
    width: 100%; height: 100%;
    object-fit: cover;
  }

  .member-details {
    display: flex; flex-direction: column;
    gap: 2px; min-width: 0;
  }

  .member-name-row {
    display: flex; align-items: center;
    gap: 8px; flex-wrap: wrap;
  }

  .username {
    font-weight: 800; font-size: 0.95rem;
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .user-id-tag {
    font-size: 0.72rem;
    color: var(--rf-text-muted, rgb(100, 116, 139));
    font-family: monospace;
  }

  .character-tag {
    font-size: 0.78rem;
    color: var(--rf-text-secondary, rgb(75, 85, 99));
    font-weight: 600;
    display: inline-flex; align-items: center; gap: 4px;
  }

  .member-controls {
    display: flex; align-items: center;
    gap: 12px; flex-shrink: 0;
  }

  /* Empty State */
  .empty-state {
    padding: 40px 20px; text-align: center;
    display: flex; flex-direction: column;
    align-items: center; gap: 10px;
  }

  .empty-icon { font-size: 2.2rem; }

  .empty-title {
    font-size: 1.1rem; font-weight: 800;
    margin: 0;
  }

  .empty-desc {
    font-size: 0.85rem;
    color: var(--rf-text-muted, rgb(100, 116, 139));
    max-width: 360px;
    margin: 0;
  }
`;
