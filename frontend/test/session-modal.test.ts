/**
 * Unit tests for Session Modal and Session List components.
 * TASK-0249: Session Scheduling and Staging Lobby Creation Modal
 * Governed by ADR-0001, ADR-0004, ADR-0007, ADR-0012.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const ROOT_DIR = resolve(process.cwd());
const MODAL_PATH = resolve(ROOT_DIR, 'src/components/runefoble-session-modal.ts');
const LIST_PATH = resolve(ROOT_DIR, 'src/components/runefoble-session-list.ts');
const STORIES_PATH = resolve(ROOT_DIR, 'src/stories/runefoble-session-modal.stories.ts');

describe('Session Modal & List Component Contracts (TASK-0249)', () => {
  it('runefoble-session-modal.ts exists and satisfies file length limit (<500 lines)', () => {
    const content = readFileSync(MODAL_PATH, 'utf-8');
    const lines = content.split('\n');
    assert.ok(lines.length < 500, `Modal file has ${lines.length} lines, must be < 500`);
    assert.ok(content.includes("@customElement('runefoble-session-modal')"));
    assert.ok(content.includes('class RunefobleSessionModal extends LitElement'));
  });

  it('runefoble-session-list.ts satisfies file length limit and integrates session modal', () => {
    const content = readFileSync(LIST_PATH, 'utf-8');
    const lines = content.split('\n');
    assert.ok(lines.length < 500, `List file has ${lines.length} lines, must be < 500`);
    assert.ok(content.includes("import './runefoble-session-modal.ts'"));
    assert.ok(content.includes('<runefoble-session-modal'));
    assert.ok(content.includes('isCreateModalOpen'));
    assert.ok(content.includes('openCreateModal'));
    assert.ok(content.includes('closeCreateModal'));
  });

  it('modal declares all required form fields, status options, and actions', () => {
    const content = readFileSync(MODAL_PATH, 'utf-8');
    // Field IDs and names
    assert.ok(content.includes('id="session-title"'));
    assert.ok(content.includes('id="session-status"'));
    assert.ok(content.includes('id="scheduled-at"'));
    assert.ok(content.includes('id="session-description"'));
    // Status options
    assert.ok(content.includes('value="lobby"'));
    assert.ok(content.includes('value="upcoming"'));
    // Actions and buttons
    assert.ok(content.includes('class="btn-cancel"'));
    assert.ok(content.includes('class="btn-submit"'));
    assert.ok(content.includes('class="btn-close"'));
    // Accessibility attributes
    assert.ok(content.includes('role="dialog"'));
    assert.ok(content.includes('aria-modal="true"'));
    assert.ok(content.includes('aria-labelledby="session-modal-title"'));
  });

  it('modal dispatches @create-session with title, status, scheduledAt, and description', () => {
    const content = readFileSync(MODAL_PATH, 'utf-8');
    assert.ok(content.includes("new CustomEvent('create-session'"));
    assert.ok(content.includes('title: this.sessionTitle.trim()'));
    assert.ok(content.includes('status: this.status'));
    assert.ok(content.includes('scheduledAt:'));
    assert.ok(content.includes('description:'));
    assert.ok(content.includes('bubbles: true'));
    assert.ok(content.includes('composed: true'));
  });

  it('modal validates title and handles validation errors', () => {
    const content = readFileSync(MODAL_PATH, 'utf-8');
    assert.ok(content.includes('Session title is required'));
    assert.ok(content.includes('error-banner'));
    assert.ok(content.includes('role="alert"'));
  });

  it('Storybook stories exist and cover lobby, upcoming, validation error, and themes', () => {
    const content = readFileSync(STORIES_PATH, 'utf-8');
    assert.ok(content.includes("title: 'Campaign/RunefobleSessionModal'"));
    assert.ok(content.includes('DefaultOpenLobby'));
    assert.ok(content.includes('OpenUpcomingSession'));
    assert.ok(content.includes('ModalWithValidationError'));
    assert.ok(content.includes('DarkMode'));
    assert.ok(content.includes('LightMode'));
  });
});
