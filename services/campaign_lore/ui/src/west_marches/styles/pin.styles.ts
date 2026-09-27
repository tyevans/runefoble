import { css } from 'lit';

export const pinStyles = css`
  :host {
    display: block;
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }
  .pins-svg { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }
  .outpost-marker, .pin-marker { cursor: pointer; pointer-events: auto; }
  .outpost-circle { fill: #2a9d8f; stroke: #121212; stroke-width: 2.5px; }
  .pin-marker:hover { transform: scale(1.3); }
  .pin-circle { stroke: #121212; stroke-width: 2px; }
  .pin-tag {
    font-size: 10px; font-weight: 800; fill: #121212;
    text-shadow: 1px 1px 0px #fff, -1px -1px 0px #fff; pointer-events: none;
  }
  .pin-danger { font-size: 8px; font-weight: 900; fill: #ffffff; text-anchor: middle; pointer-events: none; }
  .inspection-popover {
    position: absolute; bottom: 20px; right: 20px; width: 320px;
    background: #ffffff; border: 2px solid #121212; box-shadow: 4px 4px 0px #121212;
    padding: 14px; z-index: 25; display: flex; flex-direction: column; gap: 8px; pointer-events: auto;
  }
  .popover-header { display: flex; justify-content: space-between; align-items: flex-start; }
  .popover-title { font-size: 1rem; font-weight: 800; margin: 0; }
  .popover-close { background: transparent; border: none; font-weight: 800; font-size: 1.1rem; cursor: pointer; }
  .badge-row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .type-badge, .danger-badge, .attribution-badge { font-size: 0.7rem; font-weight: 700; padding: 2px 6px; border: 1px solid #121212; }
  .type-badge { background: #f1faee; text-transform: uppercase; }
  .danger-badge { background: #e63946; color: #ffffff; font-weight: 800; }
  .attribution-badge { background: #ffb703; }
  .popover-desc { font-size: 0.8rem; color: #333; line-height: 1.35; }
  .popover-notes { font-size: 0.76rem; padding: 6px 8px; background: #f8f9fa; border-left: 3px solid #457b9d; color: #444; }
  .zanzibar-notice { font-size: 0.68rem; font-style: italic; color: #666; background: #fefae0; padding: 4px 6px; border: 1px dashed #d4a373; }
`;
