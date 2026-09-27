import { css } from 'lit';

export const whisperStyles = css`
  :host {
    display: block;
  }

  .whisper-card {
    background: #1e1b4b;
    color: #e0e7ff;
    border: 2px solid #818cf8;
    border-radius: 4px;
    padding: 14px;
    box-shadow: 0 0 12px rgba(129, 140, 248, 0.4);
    animation: whisper-glow 2s infinite alternate;
    position: relative;
  }

  @keyframes whisper-glow {
    0% { border-color: #818cf8; box-shadow: 0 0 8px rgba(129, 140, 248, 0.3); }
    100% { border-color: #c084fc; box-shadow: 0 0 16px rgba(192, 132, 252, 0.6); }
  }

  .whisper-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 800;
    font-size: 0.85rem;
    text-transform: uppercase;
    color: #a5b4fc;
    margin-bottom: 8px;
  }

  .whisper-body {
    position: relative;
    font-style: italic;
    font-size: 0.95rem;
    line-height: 1.4;
    cursor: pointer;
    min-height: 2.4em;
    display: flex;
    align-items: center;
    user-select: text;
  }

  .whisper-body.content-blurred {
    filter: blur(6px);
    user-select: none;
    opacity: 0.7;
    transition: filter 0.2s ease, opacity 0.2s ease;
  }

  .blur-overlay-hint {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.8rem;
    color: #fef08a;
    background: rgba(30, 27, 75, 0.55);
    border: 1px dashed #fef08a;
    border-radius: 2px;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    z-index: 2;
  }

  .whisper-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 10px;
  }

  .turn-card {
    background: #7f1d1d;
    color: #fef2f2;
    border: 2px solid #f87171;
    border-radius: 4px;
    padding: 12px;
    animation: turn-pulse 1s infinite alternate;
  }

  @keyframes turn-pulse {
    0% { transform: scale(1); }
    100% { transform: scale(1.01); }
  }

  .turn-title {
    font-weight: 900;
    font-size: 1rem;
    text-transform: uppercase;
  }
`;
