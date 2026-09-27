import { css } from 'lit';

export const compendiumStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, 'Space Grotesk', system-ui, sans-serif);
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    padding: 18px;
    box-sizing: border-box;
    max-width: 1000px;
    margin: 0 auto;
  }
  .compendium-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
  }
  .title-group {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .main-title {
    font-size: 1.35rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .subtitle {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--rf-text-secondary, #555555);
  }
  .latency-badge {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 8px;
    background: #d8f3dc;
    color: #1b4332;
    border: 1px solid #121212;
    box-shadow: 2px 2px 0px #121212;
    letter-spacing: 0.02em;
  }
  .tabs-nav {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .tab-btn {
    background: var(--rf-bg-surface, #ffffff);
    border: 2px solid var(--rf-border-color, #121212);
    padding: 6px 14px;
    font-family: inherit;
    font-size: 0.82rem;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 2px 2px 0px #121212;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .tab-btn:hover {
    transform: translate(-1px, -1px);
    box-shadow: 3px 3px 0px #121212;
  }
  .tab-btn:active {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px #121212;
  }
  .tab-btn.active {
    background: var(--rf-accent-primary, #d90429);
    color: #ffffff;
  }
  .section-panel {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .search-bar-row {
    display: flex;
    gap: 8px;
    align-items: stretch;
  }
  .search-input {
    flex: 1;
    padding: 8px 12px;
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: 600;
    border: 2px solid #121212;
    box-shadow: 2px 2px 0px #121212;
    outline: none;
    box-sizing: border-box;
  }
  .search-input:focus {
    border-color: #d90429;
  }
  .action-btn {
    background: #ffb703;
    color: #121212;
    border: 2px solid #121212;
    padding: 8px 16px;
    font-family: inherit;
    font-size: 0.85rem;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 2px 2px 0px #121212;
    text-transform: uppercase;
  }
  .action-btn:hover { background: #fca311; }
  .action-btn.primary { background: #d90429; color: #ffffff; }
  .action-btn.primary:hover { background: #b70020; }
  .action-btn.secondary { background: #e2eafc; }
  .filter-pills {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
  }
  .filter-pill {
    padding: 3px 10px;
    font-size: 0.75rem;
    font-weight: 700;
    border: 1px solid #121212;
    background: #f8f9fa;
    cursor: pointer;
    box-shadow: 1px 1px 0px #121212;
  }
  .filter-pill.active {
    background: #121212;
    color: #ffffff;
  }
  .results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    margin-top: 8px;
    max-height: 480px;
    overflow-y: auto;
    padding-right: 4px;
  }
  .result-card {
    border: 2px solid #121212;
    background: #ffffff;
    padding: 12px;
    box-shadow: 3px 3px 0px #121212;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 6px;
  }
  .rule-title {
    font-size: 1rem;
    font-weight: 800;
    margin: 0;
  }
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
  .summary-text {
    font-size: 0.8rem;
    line-height: 1.35;
    color: #333333;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .details-bar {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    font-size: 0.75rem;
    font-weight: 700;
    background: #f1f3f5;
    padding: 4px 6px;
    border: 1px solid #121212;
  }
  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: auto;
    gap: 6px;
  }
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
  .stat-block-expanded {
    border: 2px solid #121212;
    background: #fffdf0;
    padding: 14px;
    box-shadow: 4px 4px 0px #121212;
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 4px;
    text-align: center;
    background: #ffffff;
    border: 1px solid #121212;
    padding: 6px;
  }
  .stat-cell-title {
    font-size: 0.65rem;
    font-weight: 800;
  }
  .stat-cell-val {
    font-size: 0.85rem;
    font-weight: 700;
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
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .form-label {
    font-size: 0.78rem;
    font-weight: 800;
    text-transform: uppercase;
  }
  .form-input, .form-select, .form-textarea {
    padding: 6px 10px;
    font-family: inherit;
    font-size: 0.85rem;
    border: 2px solid #121212;
    box-shadow: 2px 2px 0px #121212;
    box-sizing: border-box;
  }
  .form-textarea {
    resize: vertical;
    min-height: 60px;
  }
  .form-grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
`;
