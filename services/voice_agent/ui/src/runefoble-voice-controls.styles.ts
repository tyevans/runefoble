import { css } from 'lit';

export const voiceControlsStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary);
  }
  .voice-control-panel {
    background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    box-shadow: var(--rf-shadow);
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    box-sizing: border-box;
    transition: background-color 0.2s ease, border-color 0.2s ease;
  }
  .header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
  }
  .channel-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .status-indicator {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background-color: var(--rf-text-muted);
    display: inline-block;
    transition: background-color 0.2s ease;
  }
  .status-indicator.live {
    background-color: var(--rf-accent-primary);
    box-shadow: 0 0 6px var(--rf-accent-primary);
    animation: pulse-dot 1.5s infinite;
  }
  @keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .channel-title {
    font-weight: 700;
    font-size: 1rem;
    color: var(--rf-text-primary);
  }
  .status-badges {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .badge {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 8px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm);
    border-radius: var(--rf-border-radius, 0px);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .badge-webrtc.connected { background: var(--rf-bg-surface); color: var(--rf-accent-secondary); }
  .badge-webrtc.disconnected { background: var(--rf-bg-canvas); color: var(--rf-text-muted); }
  .badge-webrtc.connecting, .badge-webrtc.reconnecting { background: var(--rf-accent-tertiary); color: var(--rf-text-primary); }
  .badge-webrtc.failed { background: var(--rf-accent-primary); color: var(--rf-text-inverse); }
  .badge-warning { background: var(--rf-accent-primary); color: var(--rf-text-inverse); animation: pulse-warning 1.8s infinite; }
  .badge-dsp { background: var(--rf-accent-tertiary); color: var(--rf-text-primary); }
  @keyframes pulse-warning {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.75; }
  }
  .main-controls-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }
  .visualizer-wrapper {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    min-width: 260px;
  }
  .canvas-container {
    background: var(--rf-bg-inset, var(--rf-bg-canvas));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm);
    border-radius: var(--rf-border-radius, 0px);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    flex: 1;
    height: 44px;
  }
  .waveform-canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
  .metrics-panel {
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 0.72rem;
    font-family: monospace;
    font-weight: 700;
    color: var(--rf-text-muted);
    min-width: 90px;
  }
  .mic-button {
    background: var(--rf-accent-primary);
    color: var(--rf-text-inverse);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px);
    box-shadow: var(--rf-shadow-sm);
    padding: 10px 18px;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: inherit;
    white-space: nowrap;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .mic-button:hover:not(:disabled) {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow);
  }
  .mic-button:active:not(:disabled) {
    transform: translate(1px, 1px);
    box-shadow: none;
  }
  .mic-button:disabled { opacity: 0.5; cursor: not-allowed; }
  .mic-button.listening { background: var(--rf-accent-tertiary); color: var(--rf-text-primary); }
  .panel-instruction {
    font-size: 0.8rem;
    color: var(--rf-text-muted);
  }
`;
