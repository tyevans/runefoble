import { css } from 'lit';

export const soundscapeControlsStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, 'Space Grotesk', system-ui, sans-serif);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    border-radius: var(--rf-border-radius, 0px);
    padding: 16px;
    color: var(--rf-text-primary, #121212);
    width: 440px;
    max-width: 100%;
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    box-sizing: border-box;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 8px;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    margin-bottom: 12px;
  }

  .title {
    font-size: 1.05rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    text-transform: uppercase;
  }

  .badge-row {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .badge-mood {
    padding: 3px 8px;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    border: 1px solid var(--rf-border-color, #121212);
    box-shadow: 1px 1px 0px #121212;
  }

  .badge-mood.exploration {
    background: var(--rf-accent-secondary, #2a9d8f);
    color: #ffffff;
  }

  .badge-mood.tension {
    background: var(--rf-accent-tertiary, #e9c46a);
    color: #121212;
  }

  .badge-mood.combat {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
  }

  .badge-mood.boss {
    background: #6a0572;
    color: #ffffff;
  }

  .badge-ducked {
    padding: 3px 6px;
    font-size: 0.7rem;
    font-weight: 800;
    background: #ffb703;
    color: #121212;
    border: 1px solid var(--rf-border-color, #121212);
    box-shadow: 1px 1px 0px #121212;
    animation: pulse 1.5s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }

  .section {
    margin-bottom: 12px;
  }

  .section-label {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
  }

  .tension-bar {
    width: 100%;
    height: 12px;
    background: #eee;
    border: 1px solid var(--rf-border-color, #121212);
    overflow: hidden;
  }

  .tension-fill {
    height: 100%;
    transition: width 0.4s ease, background 0.4s ease;
  }

  .slider-control {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  input[type='range'] {
    flex: 1;
    accent-color: var(--rf-accent-primary, #e63946);
    cursor: pointer;
  }

  .volume-val {
    font-size: 0.8rem;
    font-weight: 800;
    width: 38px;
    text-align: right;
  }

  .stem-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }

  .stem-pill {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 8px;
    background: #f7f7f7;
    border: 1px solid var(--rf-border-color, #121212);
    font-size: 0.75rem;
    font-weight: 700;
  }

  .stem-pill.active {
    border-left: 4px solid var(--rf-accent-primary, #e63946);
    background: #fff0f0;
  }

  .mood-buttons {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .mood-btn {
    flex: 1;
    min-width: 80px;
    padding: 6px 4px;
    font-size: 0.75rem;
    font-weight: 800;
    background: #ffffff;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    cursor: pointer;
    box-shadow: 2px 2px 0px #121212;
  }

  .mood-btn:hover {
    background: #f0f0f0;
  }

  .mood-btn.selected {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
  }

  .foley-buttons {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .cue-btn {
    padding: 5px 8px;
    font-size: 0.75rem;
    font-weight: 700;
    background: #121212;
    color: #ffffff;
    border: 1px solid #121212;
    cursor: pointer;
  }

  .cue-btn:hover {
    background: var(--rf-accent-primary, #e63946);
  }
`;
