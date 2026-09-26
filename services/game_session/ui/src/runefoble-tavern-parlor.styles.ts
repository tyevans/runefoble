import { css } from 'lit';

export const tavernParlorStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #1e293b);
    background: var(--rf-surface, #f8fafc);
    border: var(--rf-border-width, 3px) solid var(--rf-border-color, #0f172a);
    box-shadow: var(--rf-shadow-hard, 5px 5px 0px #0f172a);
    max-width: 900px;
    margin: 0 auto;
    padding: 24px;
  }

  * {
    box-sizing: border-box;
  }

  .header-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid var(--rf-border-color, #0f172a);
    padding-bottom: 14px;
    margin-bottom: 18px;
  }

  .title-group h2 {
    margin: 0;
    font-size: 1.4rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .title-group p {
    margin: 4px 0 0 0;
    color: var(--rf-text-muted, #64748b);
    font-size: 0.85rem;
  }

  /* Navigation Tabs */
  .tab-bar {
    display: flex;
    gap: 8px;
    margin-bottom: 18px;
  }

  .tab-btn {
    background: #e2e8f0;
    border: 2px solid #0f172a;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 0.85rem;
    text-transform: uppercase;
    cursor: pointer;
    box-shadow: 2px 2px 0px #0f172a;
    transition: all 0.15s ease;
  }

  .tab-btn.active {
    background: #f59e0b;
    color: #ffffff;
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px #0f172a;
  }

  /* Panels */
  .panel {
    background: #ffffff;
    border: 2px solid #0f172a;
    padding: 16px;
    box-shadow: 3px 3px 0px #0f172a;
  }

  /* 3D Dice Cup & Shaker Stage */
  .shaker-stage {
    perspective: 800px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #1e1e24;
    border: 2px solid #0f172a;
    padding: 24px;
    margin-bottom: 16px;
    min-height: 180px;
  }

  .dice-cup {
    width: 80px;
    height: 100px;
    background: linear-gradient(135deg, #78350f, #b45309);
    border: 3px solid #fef08a;
    border-radius: 8px 8px 30px 30px;
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.4);
    transform: rotateX(15deg);
    transition: transform 0.2s ease;
    cursor: pointer;
  }

  .dice-cup.shaking {
    animation: shakeCup 0.4s infinite ease-in-out;
  }

  @keyframes shakeCup {
    0% { transform: rotateX(15deg) rotateZ(0deg) translateY(0); }
    25% { transform: rotateX(25deg) rotateZ(-12deg) translateY(-8px); }
    50% { transform: rotateX(10deg) rotateZ(10deg) translateY(6px); }
    75% { transform: rotateX(20deg) rotateZ(-8deg) translateY(-4px); }
    100% { transform: rotateX(15deg) rotateZ(0deg) translateY(0); }
  }

  /* Dice Tray */
  .dice-tray {
    display: flex;
    gap: 10px;
    margin-top: 14px;
    flex-wrap: wrap;
    justify-content: center;
  }

  .die-box {
    width: 44px;
    height: 44px;
    background: #f8fafc;
    border: 2px solid #0f172a;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    font-weight: 800;
    box-shadow: 3px 3px 0px #0f172a;
    border-radius: 4px;
  }

  .die-box.wild {
    background: #fef08a;
    border-color: #ca8a04;
  }

  /* Bidding Controls */
  .bidding-controls {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 14px;
  }

  .stepper-group {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #f1f5f9;
    padding: 8px;
    border: 1px solid #cbd5e1;
  }

  .stepper-btn {
    width: 32px;
    height: 32px;
    font-weight: 800;
    border: 2px solid #0f172a;
    background: #ffffff;
    cursor: pointer;
  }

  /* Buttons */
  .btn {
    border: 2px solid #0f172a;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 0.9rem;
    cursor: pointer;
    box-shadow: 2px 2px 0px #0f172a;
    text-transform: uppercase;
    transition: transform 0.1s ease;
  }

  .btn:active {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px #0f172a;
  }

  .btn-gold {
    background: #f59e0b;
    color: #ffffff;
  }

  .btn-challenge {
    background: #ef4444;
    color: #ffffff;
  }

  .btn-drink {
    background: #0284c7;
    color: #ffffff;
  }

  /* Intoxication Meter */
  .intoxication-section {
    margin-top: 14px;
  }

  .intox-bar {
    height: 14px;
    background: #e2e8f0;
    border: 2px solid #0f172a;
    overflow: hidden;
    margin: 8px 0;
  }

  .intox-fill {
    height: 100%;
    transition: width 0.3s ease;
  }

  .intox-fill.sober { width: 10%; background: #22c55e; }
  .intox-fill.tipsy { width: 35%; background: #eab308; }
  .intox-fill.drunk { width: 65%; background: #f97316; }
  .intox-fill.smashed { width: 85%; background: #ef4444; }
  .intox-fill.blackout { width: 100%; background: #7f1d1d; }

  /* DSP Badge */
  .dsp-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    background: #ede9fe;
    color: #6d28d9;
    border: 1px solid #c4b5fd;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
  }

  /* Voice Bark Dialogue Box */
  .voice-bark-box {
    background: #fffbeb;
    border: 2px solid #b45309;
    border-left: 6px solid #d97706;
    padding: 12px;
    margin-top: 14px;
    font-style: italic;
    font-size: 0.9rem;
  }

  /* Merchant Haggling Styles */
  .merchant-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .temperament-tag {
    display: inline-block;
    padding: 4px 8px;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    border: 1px solid #0f172a;
    background: #fed7aa;
  }

  .counter-badge {
    background: #dcfce7;
    border: 2px solid #16a34a;
    color: #15803d;
    padding: 8px;
    font-weight: 800;
    text-align: center;
    margin: 10px 0;
  }
`;
