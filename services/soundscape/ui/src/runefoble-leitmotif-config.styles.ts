import { css } from 'lit';

export const leitmotifConfigStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, 'Space Grotesk', system-ui, sans-serif);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 16px;
    color: var(--rf-text-primary, #121212);
    width: 460px;
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
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .badge-row {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .badge-timbre {
    padding: 3px 8px;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    background: var(--rf-accent-secondary, #2a9d8f);
    color: #ffffff;
    border: 1px solid var(--rf-border-color, #121212);
    box-shadow: 1px 1px 0px #121212;
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
    margin-bottom: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .char-row {
    display: flex;
    gap: 8px;
    margin-bottom: 10px;
  }
  .input-field {
    flex: 1;
    font-family: inherit;
    font-size: 0.8rem;
    padding: 6px 8px;
    border: 1px solid var(--rf-border-color, #121212);
    background: #f8f9fa;
  }
  .timbre-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    margin-bottom: 10px;
  }
  .timbre-btn {
    padding: 8px 6px;
    font-size: 0.75rem;
    font-weight: 700;
    background: #ffffff;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    cursor: pointer;
    box-shadow: 2px 2px 0px #121212;
    text-align: center;
    transition: transform 0.05s ease;
  }
  .timbre-btn:hover { background: #f0f0f0; }
  .timbre-btn:active { transform: translate(1px, 1px); }
  .timbre-btn.selected {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
  }
  .slider-control {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  input[type='range'] {
    flex: 1;
    accent-color: var(--rf-accent-primary, #e63946);
    cursor: pointer;
  }
  .slider-val {
    font-size: 0.8rem;
    font-weight: 800;
    width: 48px;
    text-align: right;
  }
  .audition-row {
    display: flex;
    gap: 8px;
    margin-top: 10px;
  }
  .audition-btn {
    flex: 1;
    padding: 8px 10px;
    font-size: 0.8rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    cursor: pointer;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: 2px 2px 0px #121212;
    transition: transform 0.05s ease;
  }
  .audition-btn:active { transform: translate(1px, 1px); }
  .audition-btn.triumphant {
    background: var(--rf-accent-tertiary, #e9c46a);
    color: #121212;
  }
  .audition-btn.somber {
    background: #6a0572;
    color: #ffffff;
  }
  .audition-btn.save {
    background: var(--rf-accent-secondary, #2a9d8f);
    color: #ffffff;
  }
  .playback-indicator {
    margin-top: 10px;
    padding: 6px 10px;
    font-size: 0.75rem;
    font-weight: 700;
    background: #eaf4f4;
    border: 1px solid var(--rf-accent-secondary, #2a9d8f);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
`;
