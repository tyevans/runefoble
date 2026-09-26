import { css } from 'lit';

export const ghostStyles = css`
  .vector-overlay {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 15;
  }

  .vector-line {
    stroke: var(--rf-accent-primary);
    stroke-width: 3.5px;
    stroke-linecap: round;
    stroke-dasharray: 8 6;
    animation: dash-flow 0.8s linear infinite;
  }

  @keyframes dash-flow {
    from {
      stroke-dashoffset: 28;
    }
    to {
      stroke-dashoffset: 0;
    }
  }

  .ghost-token {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 0.75rem;
    color: var(--rf-text-inverse);
    opacity: 0.55;
    background: var(--rf-accent-secondary);
    border: 2px dashed var(--rf-accent-tertiary);
    box-shadow: 0 0 10px rgba(255, 183, 3, 0.6);
    animation: ghost-pulse 1.4s infinite ease-in-out;
    cursor: pointer;
    z-index: 12;
    transition: opacity 0.2s, transform 0.2s;
  }

  .ghost-token:hover {
    opacity: 0.9;
    transform: scale(1.14);
  }

  @keyframes ghost-pulse {
    0%,
    100% {
      box-shadow: 0 0 0 0 rgba(255, 183, 3, 0.7);
    }
    50% {
      box-shadow: 0 0 0 6px rgba(255, 183, 3, 0.2);
    }
  }

  .distance-ruler {
    position: absolute;
    bottom: -36px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--rf-color-dark);
    color: var(--rf-text-inverse);
    border: var(--rf-border-width, 2px) solid var(--rf-accent-tertiary);
    padding: 4px 10px;
    font-size: 0.8rem;
    font-weight: 800;
    box-shadow: var(--rf-shadow-sm);
    display: flex;
    align-items: center;
    gap: 6px;
    z-index: 25;
    white-space: nowrap;
    border-radius: var(--rf-border-radius, 0px);
  }

  .ghost-banner {
    margin-top: 14px;
    background: var(--rf-bg-canvas);
    border: var(--rf-border-width, 2px) solid var(--rf-accent-tertiary);
    padding: 10px 14px;
    box-shadow: var(--rf-shadow-sm);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
  }

  .ghost-info {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.85rem;
    font-weight: 700;
  }

  .ghost-timer {
    background: var(--rf-accent-tertiary);
    color: var(--rf-color-dark);
    padding: 2px 6px;
    font-size: 0.75rem;
    font-weight: 800;
    border-radius: 2px;
  }

  .ghost-actions {
    display: flex;
    gap: 8px;
  }

  .btn {
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    padding: 5px 12px;
    font-weight: 800;
    font-size: 0.8rem;
    cursor: pointer;
    box-shadow: var(--rf-shadow-sm);
    transition: transform 0.1s, box-shadow 0.1s;
  }

  .btn:active {
    transform: translate(1px, 1px);
    box-shadow: none;
  }

  .btn-confirm {
    background: var(--rf-accent-tertiary);
    color: var(--rf-color-dark);
  }

  .btn-cancel {
    background: var(--rf-bg-surface);
    color: var(--rf-text-primary);
  }
`;
