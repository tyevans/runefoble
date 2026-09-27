import { css } from 'lit';

export const badgeStyles = css`
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
`;
