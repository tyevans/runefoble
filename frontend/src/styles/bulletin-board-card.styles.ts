import { css } from 'lit';

export const bulletinBoardCardStyles = css`
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
`;
