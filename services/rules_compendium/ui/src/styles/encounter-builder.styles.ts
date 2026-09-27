import { css } from 'lit';

export const encounterBuilderStyles = css`
  .category-tag {
    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
    padding: 2px 6px;
    border: 1px solid #121212;
    background: #e2eafc;
  }
  .category-tag.monster { background: #ffccd5; color: #800f2f; }
  .category-tag.spell { background: #d8bbff; color: #3c096c; }
  .category-tag.condition { background: #ffe5d9; color: #9d0208; }
  .category-tag.homebrew { background: #ffb703; color: #121212; }
  .small-btn {
    padding: 4px 8px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: inherit;
    border: 1px solid #121212;
    background: #ffffff;
    cursor: pointer;
    box-shadow: 1px 1px 0px #121212;
  }
  .small-btn.add {
    background: #d8f3dc;
    color: #1b4332;
  }
  .builder-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  @media (max-width: 768px) {
    .builder-layout {
      grid-template-columns: 1fr;
    }
  }
  .roster-card {
    border: 2px solid #121212;
    padding: 12px;
    box-shadow: 3px 3px 0px #121212;
    background: #ffffff;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .threshold-bar {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 4px;
    text-align: center;
    border: 1px solid #121212;
    background: #f8f9fa;
    padding: 6px;
  }
  .threshold-item {
    font-size: 0.72rem;
    font-weight: 700;
  }
  .threshold-item.easy { color: #2d6a4f; }
  .threshold-item.medium { color: #0077b6; }
  .threshold-item.hard { color: #d00000; }
  .threshold-item.deadly { color: #5a189a; }
  .lethality-status-box {
    border: 2px solid #121212;
    padding: 10px;
    font-weight: 800;
    text-align: center;
    text-transform: uppercase;
    font-size: 1.1rem;
    box-shadow: 2px 2px 0px #121212;
  }
  .lethality-status-box.easy { background: #d8f3dc; color: #1b4332; }
  .lethality-status-box.medium { background: #caf0f8; color: #03045e; }
  .lethality-status-box.hard { background: #ffccd5; color: #590d22; }
  .lethality-status-box.deadly { background: #e0aaff; color: #240046; }
  .draft-monster-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 250px;
    overflow-y: auto;
  }
  .draft-monster-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid #121212;
    padding: 6px 10px;
    background: #fafafa;
  }
  .qty-controls {
    display: flex;
    gap: 4px;
    align-items: center;
  }
  .qty-btn {
    width: 22px;
    height: 22px;
    border: 1px solid #121212;
    background: #ffffff;
    font-weight: 800;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }
`;
