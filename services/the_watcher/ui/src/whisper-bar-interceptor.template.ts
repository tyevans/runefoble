/**
 * The pending action box of the DM whisper bar (TASK-0949).
 *
 * An open action shows the pause window and the Approve, Veto and Edit controls. A vetoed action
 * shows the outcome and no control, because the action no longer runs.
 */

import { html, type TemplateResult } from 'lit';
import type { PendingActionItem } from './whisper-bar-types.ts';

export interface InterceptorView {
  action: PendingActionItem;
  remainingMs: number;
  totalMs: number;
  isEditing: boolean;
  editDescription: string;
  editTarget: string;
  actionError: string;
}

export interface InterceptorHandlers {
  approve: () => void;
  veto: () => void;
  startEdit: () => void;
  cancelEdit: () => void;
  saveEdit: () => void;
  editDescription: (value: string) => void;
  editTarget: (value: string) => void;
}

function renderEditForm(view: InterceptorView, on: InterceptorHandlers): TemplateResult {
  return html`
    <div class="edit-form">
      <div class="form-row">
        <label>Description</label>
        <input type="text" .value=${view.editDescription}
          @input=${(e: Event) => on.editDescription((e.target as HTMLInputElement).value)} />
      </div>
      <div class="form-row">
        <label>Target</label>
        <input type="text" .value=${view.editTarget}
          @input=${(e: Event) => on.editTarget((e.target as HTMLInputElement).value)} />
      </div>
      <div class="action-controls" style="margin-top: 6px;">
        <button class="rf-btn btn-approve" @click=${on.saveEdit}>Save & Approve</button>
        <button class="rf-btn" @click=${on.cancelEdit}>Cancel</button>
      </div>
    </div>
  `;
}

function renderControls(on: InterceptorHandlers): TemplateResult {
  return html`
    <div class="action-controls">
      <button class="rf-btn btn-approve" @click=${on.approve}>Approve</button>
      <button class="rf-btn btn-veto" @click=${on.veto}>Veto</button>
      <button class="rf-btn btn-edit" @click=${on.startEdit}>Edit Intent</button>
    </div>
  `;
}

function renderDetails(action: PendingActionItem): TemplateResult {
  return html`
    <div class="action-details">
      <span class="action-actor">${action.actor_name}:</span>
      ${action.description}
      ${action.target ? html` &rarr; <strong>Target: ${action.target}</strong>` : ''}
    </div>
  `;
}

export function renderInterceptor(view: InterceptorView, on: InterceptorHandlers): TemplateResult {
  const { action } = view;
  if (action.status === 'vetoed') {
    return html`
      <div class="interceptor-box" data-action-status="vetoed">
        <div class="interceptor-header">
          <div class="interceptor-title">AI Action</div>
          <span class="badge badge-whisper-type">${action.action_type}</span>
        </div>
        ${renderDetails(action)}
        <div class="action-outcome" role="status">Action vetoed. It does not run.</div>
      </div>
    `;
  }
  const progressPercent = view.totalMs > 0 ? (view.remainingMs / view.totalMs) * 100 : 0;
  return html`
    <div class="interceptor-box" data-action-status=${action.status ?? 'pending'}>
      <div class="interceptor-header">
        <div class="interceptor-title">
          ⚠️ AI Action Intercepted (${Math.ceil(view.remainingMs / 1000)}s pause window)
        </div>
        <span class="badge badge-whisper-type">${action.action_type}</span>
      </div>
      <div class="countdown-bar">
        <div class="countdown-fill" style="width: ${progressPercent}%;"></div>
      </div>
      ${renderDetails(action)}
      ${view.isEditing ? renderEditForm(view, on) : renderControls(on)}
      ${view.actionError ? html`<div class="bar-error" role="alert">${view.actionError}</div>` : ''}
    </div>
  `;
}
