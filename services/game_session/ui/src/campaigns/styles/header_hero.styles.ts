import { css } from 'lit';

export const headerHeroStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, rgb(18, 18, 18));
  }

  * {
    box-sizing: border-box;
  }

  .campaign-header-card {
    background: var(--rf-bg-surface, rgb(255, 255, 255));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    box-shadow: var(--rf-shadow, 4px 4px 0px var(--rf-shadow-color, rgb(18, 18, 18)));
    overflow: hidden;
    position: relative;
  }

  /* Hero Banner */
  .hero-banner {
    position: relative;
    width: 100%;
    min-height: 160px;
    max-height: 260px;
    overflow: hidden;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, rgb(18, 18, 18));
    background: var(--rf-bg-surface-elevated, rgb(240, 240, 240));
  }

  .cover-image {
    width: 100%;
    height: 220px;
    object-fit: cover;
    display: block;
  }

  /* Bauhaus Fallback Pattern */
  .hero-banner-fallback {
    width: 100%;
    height: 180px;
    background: linear-gradient(
      135deg,
      var(--rf-accent-secondary, rgb(29, 53, 87)) 0%,
      var(--rf-accent-primary, rgb(230, 57, 70)) 65%,
      var(--rf-accent-tertiary, rgb(255, 183, 3)) 100%
    );
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .geometric-pattern {
    position: absolute;
    inset: 0;
    opacity: 0.25;
    background-image:
      linear-gradient(var(--rf-border-color, rgb(18, 18, 18)) 2px, transparent 2px),
      linear-gradient(90deg, var(--rf-border-color, rgb(18, 18, 18)) 2px, transparent 2px);
    background-size: 32px 32px;
  }

  .geometric-accent-circle {
    position: absolute;
    width: 140px;
    height: 140px;
    border-radius: 50%;
    border: 3px solid var(--rf-text-inverse, rgb(255, 255, 255));
    top: -20px;
    right: 40px;
    opacity: 0.4;
  }

  .geometric-accent-bar {
    position: absolute;
    width: 180px;
    height: 14px;
    background: var(--rf-accent-tertiary, rgb(255, 183, 3));
    bottom: 24px;
    left: -20px;
    transform: rotate(-12deg);
    border: 2px solid var(--rf-border-color, rgb(18, 18, 18));
  }

  .fallback-hero-title {
    position: relative;
    z-index: 1;
    font-size: 1.6rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--rf-text-inverse, rgb(255, 255, 255));
    text-shadow: 2px 2px 0px var(--rf-border-color, rgb(18, 18, 18));
    padding: 0 16px;
    text-align: center;
  }
`;
