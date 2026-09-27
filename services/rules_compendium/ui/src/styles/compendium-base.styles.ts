import { css } from 'lit';

export const compendiumBaseStyles = css`
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
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;
  }
  .title-group { display: flex; flex-direction: column; gap: 2px; }
  .main-title {
    font-size: 1.35rem; font-weight: 800; letter-spacing: -0.02em;
    text-transform: uppercase; display: flex; align-items: center; gap: 8px;
  }
  .subtitle { font-size: 0.8rem; font-weight: 600; color: var(--rf-text-secondary, #555555); }
  .latency-badge {
    font-size: 0.72rem; font-weight: 700; padding: 3px 8px; background: #d8f3dc;
    color: #1b4332; border: 1px solid #121212; box-shadow: 2px 2px 0px #121212; letter-spacing: 0.02em;
  }
  .tabs-nav { display: flex; gap: 6px; flex-wrap: wrap; }
  .tab-btn {
    background: var(--rf-bg-surface, #ffffff); border: 2px solid var(--rf-border-color, #121212);
    padding: 6px 14px; font-family: inherit; font-size: 0.82rem; font-weight: 700;
    cursor: pointer; box-shadow: 2px 2px 0px #121212; transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .tab-btn:hover { transform: translate(-1px, -1px); box-shadow: 3px 3px 0px #121212; }
  .tab-btn:active { transform: translate(1px, 1px); box-shadow: 1px 1px 0px #121212; }
  .tab-btn.active { background: var(--rf-accent-primary, #d90429); color: #ffffff; }
  .section-panel { display: flex; flex-direction: column; gap: 14px; }
  .search-bar-row { display: flex; gap: 8px; align-items: stretch; }
  .search-input {
    flex: 1; padding: 8px 12px; font-family: inherit; font-size: 0.9rem; font-weight: 600;
    border: 2px solid #121212; box-shadow: 2px 2px 0px #121212; outline: none; box-sizing: border-box;
  }
  .search-input:focus { border-color: #d90429; }
  .filter-pills { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .filter-pill {
    padding: 3px 10px; font-size: 0.75rem; font-weight: 700; border: 1px solid #121212;
    background: #f8f9fa; cursor: pointer; box-shadow: 1px 1px 0px #121212;
  }
  .filter-pill.active { background: #121212; color: #ffffff; }
  .results-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px; margin-top: 8px; max-height: 480px; overflow-y: auto; padding-right: 4px;
  }
  .result-card {
    border: 2px solid #121212; background: #ffffff; padding: 12px;
    box-shadow: 3px 3px 0px #121212; display: flex; flex-direction: column; gap: 8px;
  }
  .card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 6px; }
  .rule-title { font-size: 1rem; font-weight: 800; margin: 0; }
  .summary-text {
    font-size: 0.8rem; line-height: 1.35; color: #333333;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
  }
  .details-bar {
    display: flex; gap: 6px; flex-wrap: wrap; font-size: 0.75rem; font-weight: 700;
    background: #f1f3f5; padding: 4px 6px; border: 1px solid #121212;
  }
  .card-footer {
    display: flex; justify-content: space-between; align-items: center; margin-top: auto; gap: 6px;
  }
`;
