import { css } from 'lit';

export const characterCardStyles = css`
  .character-card {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 4px 4px 0px rgb(18, 18, 18));
    display: flex;
    flex-direction: column;
    padding: 16px;
    gap: 12px;
    box-sizing: border-box;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .character-card:hover {
    transform: translate(-2px, -2px);
    box-shadow: 6px 6px 0px rgb(18, 18, 18);
  }

  .card-top { display: flex; gap: 12px; align-items: center; }

  .avatar-thumb {
    width: 52px;
    height: 52px;
    border: 2px solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
    background: var(--rf-bg-canvas, rgb(248, 249, 250));
    object-fit: cover;
    flex-shrink: 0;
  }

  .card-identity { flex: 1; min-width: 0; }

  .card-name {
    font-size: 1.1rem;
    font-weight: 900;
    margin: 0 0 2px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .card-class {
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--rf-text-muted, rgb(75, 85, 99));
  }

  .card-level-badge {
    background: var(--rf-accent-tertiary, rgb(233, 196, 106));
    color: rgb(18, 18, 18);
    border: 1px solid var(--rf-border-color, rgb(18, 18, 18));
    font-size: 0.7rem;
    font-weight: 900;
    padding: 2px 6px;
    text-transform: uppercase;
  }

  .vitals-row { display: flex; flex-direction: column; gap: 6px; }
  .hp-header { display: flex; justify-content: space-between; font-size: 0.75rem; font-weight: 800; }
  .hp-bar-bg {
    height: 8px;
    background: var(--rf-bg-canvas, rgb(248, 249, 250));
    border: 1px solid var(--rf-border-color, rgb(18, 18, 18));
    overflow: hidden;
  }
  .hp-bar-fill {
    height: 100%;
    background: var(--rf-accent-secondary, rgb(42, 157, 143));
    transition: width 0.3s ease;
  }
  .hp-bar-fill.low { background: var(--rf-accent-primary, rgb(230, 57, 70)); }

  .stats-row { display: flex; gap: 8px; }
  .stat-chip {
    font-size: 0.75rem;
    font-weight: 800;
    background: var(--rf-bg-canvas, rgb(248, 249, 250));
    border: 1px solid var(--rf-border-color, rgb(18, 18, 18));
    padding: 3px 8px;
  }

  .campaign-badge {
    font-size: 0.75rem;
    font-weight: 800;
    padding: 4px 8px;
    border: 1px solid var(--rf-border-color, rgb(18, 18, 18));
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .campaign-badge.linked {
    background: rgb(230, 244, 234);
    color: rgb(19, 115, 51);
    border-color: rgb(19, 115, 51);
  }
  .campaign-badge.unassigned {
    background: var(--rf-bg-canvas, rgb(248, 249, 250));
    color: var(--rf-text-muted, rgb(75, 85, 99));
  }

  .card-actions {
    display: flex;
    gap: 6px;
    margin-top: auto;
    border-top: 1px solid var(--rf-border-color, rgb(18, 18, 18));
    padding-top: 10px;
    flex-wrap: wrap;
  }
  .card-actions .btn {
    flex: 1;
    font-size: 0.72rem;
    padding: 6px 8px;
    justify-content: center;
    min-width: 80px;
  }
`;
