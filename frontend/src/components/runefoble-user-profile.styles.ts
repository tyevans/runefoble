/**
 * Runefoble User Profile Component Styles (Bauhaus Design System)
 * ADR-0004, ADR-0012, TASK-0257
 */

import { css } from 'lit';

export const userProfileStyles = css`
  :host {
    display: block;
    width: 100%;
    max-width: 900px;
    margin: 0 auto;
    padding: 24px 16px;
    font-family: var(--rf-font-family, system-ui, sans-serif);
    color: var(--rf-text-primary, #121212);
    box-sizing: border-box;
  }

  .profile-card {
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    padding: 32px;
    display: flex;
    flex-direction: column;
    gap: 28px;
  }

  .profile-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 24px;
    flex-wrap: wrap;
  }

  .user-identity {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .avatar-large {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: var(--rf-accent-secondary, #1d3557);
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
    font-weight: 900;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    flex-shrink: 0;
  }

  .identity-text {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .profile-title {
    font-size: 1.75rem;
    font-weight: 900;
    margin: 0;
    letter-spacing: -0.5px;
    text-transform: capitalize;
  }

  .user-id-badge {
    font-size: 0.8rem;
    font-family: monospace;
    color: var(--rf-text-muted, #4b5563);
    font-weight: 700;
  }

  .btn-logout {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    padding: 8px 18px;
    font-weight: 800;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }

  .btn-logout:hover {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
  }

  .btn-logout:active {
    transform: translate(2px, 2px);
    box-shadow: none;
  }

  .section-title {
    font-size: 1.1rem;
    font-weight: 900;
    margin: 0 0 16px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--rf-text-primary, #121212);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .claims-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
  }

  .claim-item {
    background: var(--rf-bg-inset, #f8f9fa);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .claim-label {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    color: var(--rf-text-muted, #4b5563);
    letter-spacing: 0.5px;
  }

  .claim-value {
    font-size: 1rem;
    font-weight: 700;
    word-break: break-all;
  }

  .roles-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .role-badge {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    padding: 3px 8px;
    background: var(--rf-accent-tertiary, #f1faee);
    color: var(--rf-text-primary, #121212);
    border: 1px solid var(--rf-border-color, #121212);
    box-shadow: 1px 1px 0px #121212;
  }

  .role-badge.admin {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
  }

  .role-badge.dm {
    background: var(--rf-accent-secondary, #1d3557);
    color: #ffffff;
  }

  .preferences-section {
    border-top: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-top: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .controls-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }

  .control-label-group {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .control-label {
    font-weight: 800;
    font-size: 0.9rem;
  }

  .control-desc {
    font-size: 0.78rem;
    color: var(--rf-text-muted, #4b5563);
  }

  .color-mode-buttons {
    display: inline-flex;
    gap: 4px;
    background: var(--rf-bg-surface, #fff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding: 3px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
  }

  .mode-btn {
    background: none;
    border: 1px solid transparent;
    padding: 4px 10px;
    font-weight: 700;
    font-size: 0.78rem;
    cursor: pointer;
    color: var(--rf-text-primary, #121212);
  }

  .mode-btn.active {
    background: var(--rf-accent-secondary, #1d3557);
    color: #ffffff;
    border-color: var(--rf-border-color, #121212);
  }

  .btn-edit-profile {
    background: var(--rf-accent-secondary); color: var(--rf-text-on-accent, var(--rf-bg-surface));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color); box-shadow: var(--rf-shadow-sm);
    padding: 8px 18px; font-weight: 800; font-size: 0.85rem; text-transform: uppercase; cursor: pointer;
    display: inline-flex; align-items: center; gap: 6px; transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .btn-edit-profile:hover { transform: translate(-1px, -1px); box-shadow: var(--rf-shadow); }
  .header-actions { display: flex; align-items: center; gap: 12px; }
  .edit-profile-section {
    display: flex; flex-direction: column; gap: 16px; background: var(--rf-bg-subtle, var(--rf-bg-canvas));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color); padding: 20px; box-shadow: var(--rf-shadow-sm);
  }
  .edit-profile-form { display: flex; flex-direction: column; gap: 16px; }
  .form-group { display: flex; flex-direction: column; gap: 6px; }
  .form-group label { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; }
  .profile-input, .profile-textarea {
    border: var(--rf-border-width, 2px) solid var(--rf-border-color); padding: 8px 12px;
    font-family: inherit; font-size: 0.95rem; background: var(--rf-bg-surface);
    box-shadow: var(--rf-shadow-sm); color: var(--rf-text-primary);
  }
  .form-actions { display: flex; align-items: center; gap: 12px; margin-top: 8px; }
  .btn-save-profile {
    background: var(--rf-accent-tertiary); color: var(--rf-text-on-accent, var(--rf-bg-surface));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color); box-shadow: var(--rf-shadow-sm);
    padding: 8px 18px; font-weight: 800; font-size: 0.85rem; text-transform: uppercase; cursor: pointer;
  }
  .btn-cancel {
    background: none; border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    color: var(--rf-text-primary); padding: 8px 18px; font-weight: 800; font-size: 0.85rem; cursor: pointer;
  }
  .save-status { font-size: 0.85rem; font-weight: 700; color: var(--rf-accent-tertiary); }
`;
