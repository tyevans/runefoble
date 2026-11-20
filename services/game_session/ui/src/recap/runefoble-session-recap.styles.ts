import { css } from 'lit';

export const sessionRecapStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-body, inherit);
    color: var(--rf-color-text, inherit);
  }

  .session-recap {
    display: grid;
    gap: 1rem;
    padding: 1.5rem;
  }

  h2 {
    margin: 0;
    font-size: 1.5rem;
  }

  .recap-counts {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1.5rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .recap-lines {
    display: grid;
    gap: 0.5rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .recap-line {
    display: flex;
    gap: 0.75rem;
    padding: 0.5rem 0.75rem;
    border-left: 4px solid var(--rf-color-blue);
  }

  .speaker-name {
    font-weight: 700;
    white-space: nowrap;
  }
`;
