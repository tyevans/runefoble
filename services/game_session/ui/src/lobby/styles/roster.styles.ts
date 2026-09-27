import { css } from 'lit';

export const rosterStyles = css`
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
    position: relative; width: 44px; height: 44px; flex-shrink: 0;
  }
  .avatar-img {
    width: 100%; height: 100%; object-fit: cover;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
  }
  .avatar-fallback {
    width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
    background: var(--rf-accent-secondary, rgb(29, 53, 87)); color: var(--rf-text-inverse, rgb(255, 255, 255));
    font-weight: 900; font-size: 1.1rem;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
  }
  .presence-dot {
    position: absolute; bottom: -2px; right: -2px; width: 12px; height: 12px;
    border-radius: 50%; border: 2px solid var(--rf-bg-surface, rgb(255, 255, 255));
  }
  .presence-dot.online { background: rgb(34, 197, 94); }
  .presence-dot.idle { background: var(--rf-accent-tertiary, rgb(255, 183, 3)); }
  .presence-dot.offline { background: rgb(156, 163, 175); }

  .user-info { display: flex; flex-direction: column; overflow: hidden; }
  .username {
    font-weight: 800; font-size: 1rem; color: var(--rf-text-primary, rgb(18, 18, 18));
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .user-role {
    font-size: 0.75rem; font-weight: 700; color: var(--rf-text-muted, rgb(100, 116, 139));
    text-transform: uppercase; letter-spacing: 0.04em;
  }

  /* Character Preview Box */
  .character-card-preview {
    background: var(--rf-bg-inset, rgb(241, 243, 245));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding: 10px 12px; display: flex; align-items: center; gap: 10px;
  }
  .char-portrait,
  .char-portrait-fallback {
    width: 36px; height: 36px; flex-shrink: 0;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-surface, rgb(255, 255, 255));
  }
  .char-portrait { object-fit: cover; }
  .char-portrait-fallback {
    display: flex; align-items: center; justify-content: center;
    font-weight: 900; font-size: 0.9rem; color: var(--rf-text-muted, rgb(100, 116, 139));
  }
  .char-details { display: flex; flex-direction: column; overflow: hidden; }
  .char-name {
    font-weight: 800; font-size: 0.9rem; color: var(--rf-text-primary, rgb(18, 18, 18));
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .char-meta {
    font-size: 0.75rem; font-weight: 600; color: var(--rf-text-secondary, rgb(43, 45, 66));
  }
  .no-character-msg {
    font-size: 0.8rem; font-style: italic; color: var(--rf-text-muted, rgb(100, 116, 139));
  }

  /* Empty State */
  .empty-state {
    padding: 40px 24px; text-align: center;
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 4px 4px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
  }
  .empty-state h3 { margin: 0 0 8px 0; font-size: 1.2rem; font-weight: 800; }
  .empty-state p { margin: 0; color: var(--rf-text-muted, rgb(100, 116, 139)); font-size: 0.9rem; }
`;
