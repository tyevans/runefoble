import { css } from 'lit';

export const campaignMembersStyles = css`
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
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 0.95rem;
    flex-shrink: 0;
    overflow: hidden;
  }

  .avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .member-details {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .member-name-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .username {
    font-weight: 800;
    font-size: 0.95rem;
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
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .member-controls {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  /* Role Badges & Selector */
  .badge-role {
    display: inline-block;
    padding: 3px 8px;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border: 1.5px solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: 1px 1px 0px var(--rf-shadow-color, rgb(18, 18, 18));
  }

  .badge-role.role-owner,
  .badge-role.role-dm,
  .badge-role.role-dungeon_master {
    background: var(--rf-accent-tertiary, rgb(255, 183, 3));
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .badge-role.role-player {
    background: var(--rf-accent-secondary, rgb(29, 53, 87));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
  }

  .badge-role.role-spectator {
    background: var(--rf-bg-inset, rgb(241, 250, 238));
    color: var(--rf-text-secondary, rgb(75, 85, 99));
  }

  .role-select {
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding: 6px 10px;
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    font-weight: 700;
    font-size: 0.8rem;
    cursor: pointer;
    outline: none;
    transition: border-color 0.15s ease;
  }

  .role-select:focus {
    border-color: var(--rf-border-focus, rgb(255, 183, 3));
  }

  .btn-remove {
    background: transparent;
    color: var(--rf-accent-primary, rgb(230, 57, 70));
    border: var(--rf-border-width, 2px) solid var(--rf-accent-primary, rgb(230, 57, 70));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 5px 10px;
    font-weight: 800;
    font-size: 0.75rem;
    text-transform: uppercase;
    cursor: pointer;
    transition: transform 0.1s ease, background 0.1s ease, color 0.1s ease;
  }

  .btn-remove:hover {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    transform: translate(-1px, -1px);
  }

  /* Modals & Dialogs */
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
    max-width: 480px;
    padding: 24px;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding-bottom: 12px;
    margin-bottom: 18px;
  }

  .modal-title {
    font-size: 1.2rem;
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
    width: 30px;
    height: 30px;
    font-weight: 900;
    font-size: 1rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  .btn-close:hover {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
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
  }

  .form-select,
  .form-input {
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding: 8px 12px;
    background: var(--rf-bg-inset, rgb(248, 249, 250));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: 600;
    outline: none;
  }

  .invite-link-row {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-top: 10px;
  }

  .invite-link-input {
    flex: 1;
    font-family: monospace;
    font-size: 0.8rem;
    background: var(--rf-bg-inset, rgb(241, 250, 238));
  }

  .btn-copy {
    background: var(--rf-accent-secondary, rgb(29, 53, 87));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 8px 14px;
    font-weight: 800;
    font-size: 0.8rem;
    cursor: pointer;
    text-transform: uppercase;
    white-space: nowrap;
    transition: transform 0.1s ease;
  }

  .btn-copy:hover {
    transform: translate(-1px, -1px);
  }

  .copied-badge {
    display: inline-block;
    color: var(--rf-accent-tertiary, rgb(255, 183, 3));
    font-weight: 800;
    font-size: 0.75rem;
    margin-top: 4px;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 20px;
    border-top: 1px solid var(--rf-border-subtle, rgba(18, 18, 18, 0.15));
    padding-top: 16px;
  }

  .btn-cancel {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 8px 16px;
    font-weight: 800;
    font-size: 0.85rem;
    cursor: pointer;
    text-transform: uppercase;
  }

  .btn-confirm-remove {
    background: var(--rf-accent-primary, rgb(230, 57, 70));
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    padding: 8px 18px;
    font-weight: 900;
    font-size: 0.85rem;
    cursor: pointer;
    text-transform: uppercase;
  }

  /* Empty State */
  .empty-state {
    padding: 40px 20px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
  }

  .empty-icon {
    font-size: 2.2rem;
  }

  .empty-title {
    font-size: 1.1rem;
    font-weight: 800;
    margin: 0;
  }

  .empty-desc {
    font-size: 0.85rem;
    color: var(--rf-text-muted, rgb(100, 116, 139));
    max-width: 360px;
    margin: 0;
  }
`;
