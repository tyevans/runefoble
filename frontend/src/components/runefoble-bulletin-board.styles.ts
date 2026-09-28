import { css } from 'lit';

export const bulletinBoardStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, "Georgia", serif);
    color: var(--rf-text-primary, #2e1b0f);
  }

  * {
    box-sizing: border-box;
  }

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

  .empty-board-state .empty-icon {
    font-size: 3rem;
    margin-bottom: 8px;
  }

  .empty-board-state h3 {
    margin: 0 0 6px 0;
    color: #5c3a21;
  }

  .empty-board-state p {
    margin: 0;
    color: #78593d;
  }

  .notice-card {
    background: var(--rf-bg-card, #fff9eb);
    border: 1px solid var(--rf-border-subtle, #d4b896);
    border-radius: 2px;
    padding: 20px 16px 14px 16px;
    position: relative;
    cursor: pointer;
    box-shadow: 3px 5px 12px rgba(0, 0, 0, 0.22);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  .notice-card:nth-child(even) {
    transform: rotate(1.2deg);
  }

  .notice-card:nth-child(odd) {
    transform: rotate(-1.4deg);
  }

  .notice-card:hover {
    transform: translateY(-4px) rotate(0deg) scale(1.02);
    box-shadow: 4px 8px 18px rgba(0, 0, 0, 0.32);
    z-index: 5;
  }

  .push-pin {
    position: absolute;
    top: -10px;
    left: 50%;
    transform: translateX(-50%);
    width: 18px;
    height: 18px;
    background: radial-gradient(circle at 35% 35%, #ff4d4d, #990000);
    border-radius: 50%;
    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.4);
    border: 1px solid #660000;
  }

  .category-badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 3px 8px;
    border-radius: 3px;
    margin-bottom: 8px;
    color: #fff;
  }

  .category-bounty { background: #9b2226; }
  .category-rumor { background: #bb8524; }
  .category-ordinance { background: #2c4c64; }
  .category-job { background: #2a6f4e; }

  .wax-seal-badge {
    position: absolute;
    bottom: 12px;
    right: 12px;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, #d13030, #6e0d0d);
    border: 2px solid #4a0707;
    box-shadow: inset 0 0 4px rgba(0, 0, 0, 0.6), 1px 2px 4px rgba(0, 0, 0, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffcccc;
    font-size: 0.85rem;
    font-weight: bold;
  }

  .cipher-indicator {
    position: absolute;
    top: 10px;
    right: 10px;
    font-size: 0.85rem;
    color: #632b85;
    background: #eed8f7;
    padding: 2px 6px;
    border-radius: 3px;
    border: 1px solid #b78ad1;
    font-weight: bold;
  }

  .card-title {
    margin: 4px 0 8px 0;
    font-size: 1.1rem;
    font-weight: bold;
    color: #2e1b0f;
    line-height: 1.3;
  }

  .card-snippet {
    font-size: 0.85rem;
    color: #5c3a21;
    margin: 0 0 12px 0;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #78593d;
    border-top: 1px dashed #d4b896;
    padding-top: 6px;
  }

  /* Modal Backdrop & Inspection Window */
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(10, 5, 2, 0.75);
    backdrop-filter: blur(3px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 20px;
  }

  .parchment-modal {
    background: #fff9eb;
    background-image: linear-gradient(135deg, rgba(235, 220, 190, 0.4) 0%, rgba(255, 252, 245, 0.9) 100%);
    border: 2px solid #5c3a21;
    border-radius: 6px;
    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.6);
    max-width: 560px;
    width: 100%;
    padding: 28px 24px;
    position: relative;
    max-height: 90vh;
    overflow-y: auto;
  }

  .modal-close-btn {
    position: absolute;
    top: 14px;
    right: 14px;
    background: none;
    border: none;
    font-size: 1.4rem;
    color: #5c3a21;
    cursor: pointer;
  }

  .cipher-mini-puzzle {
    background: #f4ecf8;
    border: 2px solid #8e44ad;
    border-radius: 6px;
    padding: 16px;
    margin: 16px 0;
  }

  .cipher-mini-puzzle h4 {
    margin: 0 0 6px 0;
    color: #5b2c6f;
  }

  .cipher-mini-puzzle p {
    margin: 0 0 10px 0;
    font-size: 0.85rem;
    color: #4a235a;
  }

  .cipher-input-row {
    display: flex;
    gap: 8px;
  }

  .cipher-input {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid #af7ac5;
    border-radius: 4px;
    font-family: inherit;
  }

  .cipher-submit-btn {
    background: #8e44ad;
    color: #fff;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
  }

  .revealed-secret {
    background: #e8f8f5;
    border: 2px solid #1abc9c;
    border-radius: 6px;
    padding: 14px;
    margin: 16px 0;
    color: #0e6251;
  }

  .revealed-secret h4 {
    margin: 0 0 4px 0;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 20px;
    border-top: 1px solid #d4b896;
    padding-top: 14px;
  }

  .danger-btn {
    background: #9b2226;
    color: white;
    border: none;
    padding: 6px 14px;
    border-radius: 4px;
    cursor: pointer;
  }

  .secondary-btn {
    background: #5c3a21;
    color: white;
    border: none;
    padding: 6px 14px;
    border-radius: 4px;
    cursor: pointer;
  }
`;
