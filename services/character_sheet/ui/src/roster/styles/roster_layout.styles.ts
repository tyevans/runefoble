import { css } from 'lit';

export const rosterLayoutStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, rgb(18, 18, 18));
    box-sizing: border-box;
  }

  .roster-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .roster-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    padding-bottom: 16px;
    flex-wrap: wrap;
    gap: 16px;
  }

  .title-group h1 {
    font-size: 1.8rem;
    font-weight: 900;
    margin: 0 0 4px 0;
    text-transform: uppercase;
    letter-spacing: -0.5px;
  }

  .title-group p { font-size: 0.9rem; color: var(--rf-text-muted, rgb(75, 85, 99)); margin: 0; }

  .btn {
    padding: 8px 16px;
    font-size: 0.85rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    cursor: pointer;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
    transition: transform 0.1s ease, box-shadow 0.1s ease;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .btn:hover { transform: translate(-1px, -1px); box-shadow: var(--rf-shadow, 4px 4px 0px rgb(18, 18, 18)); }
  .btn:active { transform: translate(1px, 1px); box-shadow: none; }
  .btn-primary { background: var(--rf-accent-primary, rgb(230, 57, 70)); color: rgb(255, 255, 255); }
  .btn-secondary { background: var(--rf-bg-surface, rgb(255, 255, 255)); color: var(--rf-text-primary, rgb(18, 18, 18)); }
  .btn-danger { background: var(--rf-accent-primary, rgb(230, 57, 70)); color: rgb(255, 255, 255); }

  .controls-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }

  .search-input {
    flex: 1;
    min-width: 200px;
    max-width: 380px;
    padding: 8px 12px;
    font-size: 0.85rem;
    font-weight: 600;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    color: var(--rf-text-primary, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
    box-sizing: border-box;
  }
  .search-input:focus { outline: none; border-color: var(--rf-accent-secondary, rgb(29, 53, 87)); }

  .filter-pills { display: flex; gap: 6px; }

  .filter-pill {
    padding: 6px 12px;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px rgb(18, 18, 18));
    cursor: pointer;
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }
  .filter-pill.active { background: var(--rf-accent-secondary, rgb(29, 53, 87)); color: rgb(255, 255, 255); }

  .character-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 20px;
  }
`;
