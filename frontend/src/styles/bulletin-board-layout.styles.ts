import { css } from 'lit';

export const bulletinBoardLayoutStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, "Georgia", serif);
    color: var(--rf-text-primary, #2e1b0f);
  }
  * { box-sizing: border-box; }

  .bulletin-board-container {
    background: #c9a473;
    background-image: radial-gradient(#ab8553 10%, transparent 11%), radial-gradient(#ab8553 10%, transparent 11%);
    background-size: 20px 20px;
    background-position: 0 0, 10px 10px;
    border: 12px solid #4a2810;
    border-radius: 8px;
    box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.5), 0 10px 25px rgba(0, 0, 0, 0.4);
    padding: 24px;
    min-height: 520px;
    position: relative;
  }

  .board-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
    background: rgba(46, 27, 15, 0.85);
    backdrop-filter: blur(4px);
    border: 2px solid #8c532b;
    border-radius: 6px;
    padding: 12px 20px;
    margin-bottom: 24px;
    color: #fff9eb;
  }

  .board-title h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #fce8bd;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
  }
  .board-title p {
    margin: 2px 0 0 0;
    font-size: 0.85rem;
    color: #d4b896;
  }

  .board-controls {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  .tab-group, .filter-group {
    display: flex;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 4px;
    padding: 2px;
  }

  .tab-btn, .filter-btn {
    background: transparent;
    border: none;
    color: #d4b896;
    padding: 6px 12px;
    font-size: 0.85rem;
    font-family: inherit;
    cursor: pointer;
    border-radius: 3px;
    transition: all 0.2s ease;
  }
  .tab-btn.active, .filter-btn.active {
    background: #8c532b;
    color: #fff9eb;
    font-weight: bold;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
  }

  .pin-action-btn {
    background: var(--rf-accent-primary, #9b2226);
    color: #fff;
    border: 2px solid #ff6b6b;
    padding: 8px 16px;
    font-size: 0.9rem;
    font-weight: bold;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    transition: transform 0.1s ease, background 0.2s ease;
  }
  .pin-action-btn:hover {
    background: #b82b30;
    transform: translateY(-1px);
  }

  .cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 24px;
    padding: 8px;
  }

  .empty-board-state {
    grid-column: 1 / -1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 64px 20px;
    background: rgba(255, 249, 235, 0.7);
    border: 2px dashed #8c532b;
    border-radius: 8px;
    text-align: center;
  }
  .empty-board-state .empty-icon { font-size: 3rem; margin-bottom: 8px; }
  .empty-board-state h3 { margin: 0 0 6px 0; color: #5c3a21; }
  .empty-board-state p { margin: 0; color: #78593d; }
`;
