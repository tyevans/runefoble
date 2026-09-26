import { css } from 'lit';

export const campaignAnalyticsStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, 'Space Grotesk', system-ui, sans-serif);
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    padding: 20px;
    box-sizing: border-box;
    max-width: 1200px;
    margin: 0 auto;
  }

  .analytics-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 14px;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
  }

  .title-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .main-title {
    font-size: 1.4rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .campaign-meta {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--rf-text-secondary, #555555);
    display: flex;
    gap: 10px;
  }

  .tabs-nav {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .tab-btn {
    background: var(--rf-bg-surface, #ffffff);
    border: 1px solid var(--rf-border-color, #121212);
    color: var(--rf-text-primary, #121212);
    padding: 6px 14px;
    font-size: 0.8rem;
    font-weight: 800;
    text-transform: uppercase;
    cursor: pointer;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    font-family: inherit;
    transition: transform 0.1s ease;
  }

  .tab-btn:hover {
    background: var(--rf-bg-card, #f0f0f0);
    transform: translate(-1px, -1px);
  }

  .tab-btn.active {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
    box-shadow: none;
    transform: translate(1px, 1px);
  }

  .summary-metrics-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
  }

  .metric-card {
    background: var(--rf-bg-card, #fcfcfc);
    border: 1px solid var(--rf-border-color, #121212);
    padding: 12px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .metric-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--rf-text-secondary, #666);
  }

  .metric-value {
    font-size: 1.35rem;
    font-weight: 800;
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }

  @media (max-width: 900px) {
    .dashboard-grid {
      grid-template-columns: 1fr;
    }
  }

  /* Performance Infographics Styles */
  .section-panel {
    background: var(--rf-bg-surface, #ffffff);
    border: 1px solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    padding: 16px;
    margin-bottom: 20px;
  }

  .section-title {
    font-size: 1rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: -0.01em;
    border-bottom: 1px solid var(--rf-border-color, #121212);
    padding-bottom: 8px;
    margin-bottom: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .mvp-banner {
    background: var(--rf-bg-card, #fff9e6);
    border: 2px solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    padding: 14px 18px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }

  .mvp-banner-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .mvp-trophy {
    font-size: 2rem;
    line-height: 1;
  }

  .mvp-banner-title {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    color: var(--rf-accent-tertiary, #d4a373);
  }

  .mvp-recipient-name {
    font-size: 1.2rem;
    font-weight: 800;
  }

  .mvp-banner-score {
    font-size: 1.4rem;
    font-weight: 900;
    color: var(--rf-accent-primary, #e63946);
  }

  .awards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 18px;
  }

  .award-badge-card {
    background: var(--rf-bg-surface, #ffffff);
    border: 1px solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    padding: 10px 12px;
  }

  .award-badge-title {
    font-size: 0.8rem;
    font-weight: 800;
    text-transform: uppercase;
    color: var(--rf-accent-secondary, #2a9d8f);
    margin-bottom: 4px;
  }

  .award-recipient {
    font-size: 0.95rem;
    font-weight: 800;
  }

  .award-desc {
    font-size: 0.75rem;
    color: var(--rf-text-secondary, #555555);
    margin-top: 4px;
  }

  /* Bar Charts */
  .chart-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 12px;
  }

  .chart-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .chart-row-header {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    font-weight: 700;
  }

  .chart-bar-container {
    height: 14px;
    background: var(--rf-bg-inset, #eee);
    border: 1px solid var(--rf-border-color, #121212);
    position: relative;
    overflow: hidden;
    display: flex;
  }

  .bar-dealt {
    background: var(--rf-accent-primary, #e63946);
    height: 100%;
    transition: width 0.4s ease;
  }

  .bar-taken {
    background: #d4a373;
    height: 100%;
    transition: width 0.4s ease;
  }

  .bar-healing {
    background: var(--rf-accent-secondary, #2a9d8f);
    height: 100%;
    transition: width 0.4s ease;
  }

  .chart-legend {
    display: flex;
    gap: 16px;
    margin-top: 8px;
    font-size: 0.75rem;
    font-weight: 700;
  }

  .legend-dot {
    width: 10px;
    height: 10px;
    display: inline-block;
    border: 1px solid var(--rf-border-color, #121212);
    margin-right: 4px;
  }
`;
