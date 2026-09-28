"""Frontdoor tests for Project Visualizer AGY client modules and UI interactions."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.project_visualizer.assets_js import get_client_js


def test_agy_launcher_client_frontdoor_interactions(repo_root: Path):
    """Frontdoor verification of AGY modal, presets, and runner in client bundle."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js binary not found for frontdoor client testing")

    client_bundle = get_client_js(is_live_server=True)

    template_script = """
class MockElement {
  constructor(id) {
    this.id = id; this.value = ''; this.textContent = ''; this.innerHTML = '';
    this.checked = false; this.disabled = false;
    const cls = new Set();
    this.classList = {
      classes: cls,
      add: (...c) => c.forEach(x => cls.add(x)),
      remove: (...c) => c.forEach(x => cls.delete(x)),
      contains: (c) => cls.has(c),
      toggle: (c, f) => { if (f === undefined ? !cls.has(c) : f) cls.add(c); else cls.delete(c); }
    };
  }
  focus() {}
}

const ids = ['agy-modal', 'agy-modal-backdrop', 'agy-prompt-input', 'agy-target-badge',
  'agy-continue-session', 'agy-command-preview', 'agy-status-chip', 'agy-timer',
  'agy-launch-btn', 'agy-cancel-btn', 'agy-terminal-output'];
const domElements = Object.fromEntries(ids.map(id => [id, new MockElement(id)]));
domElements['agy-modal'].classList.add('hidden');
domElements['agy-modal-backdrop'].classList.add('hidden', 'opacity-0');

const window = { visualizer: {} };
global.window = window;
const listeners = [];
global.document = {
  addEventListener: (event, handler) => { listeners.push({ event, handler }); },
  getElementById: (id) => domElements[id] || null,
  querySelectorAll: () => [],
};

__CLIENT_BUNDLE__

// Seed project state with test task
window.visualizer.state = {
  data: {
    tasks: [{ id: 'TASK-0042', title: 'Tactile Token Kinematics', target_bc: 'board_state',
      file_path: 'docs/project/backlog/refined/0042-tactile-token-kinematics.md', governing_adrs: ['ADR-0004'] }]
  }
};

const hasFacadeExports = ['openAgyModal', 'closeAgyModal', 'setAgyPreset', 'updateAgyCommandPreview',
  'launchAgyForEntity', 'clearAgyOutput', 'renderTaskDrawerActions'].every(fn => typeof window.visualizer[fn] === 'function');

window.visualizer.launchAgyForEntity('TASK-0042');
const modalOpen = !domElements['agy-modal'].classList.contains('hidden');
const targetBadgeText = domElements['agy-target-badge'].textContent;
const promptVal = domElements['agy-prompt-input'].value;
const previewVal = domElements['agy-command-preview'].textContent;

window.visualizer.setAgyPreset('health_check');
const healthPromptVal = domElements['agy-prompt-input'].value;

domElements['agy-continue-session'].checked = true;
window.visualizer.updateAgyCommandPreview();
const contPreviewVal = domElements['agy-command-preview'].textContent;

const drawerBtnHtml = window.visualizer.renderTaskDrawerActions({ id: 'TASK-0042' });
domElements['agy-terminal-output'].textContent = 'Old logs';
window.visualizer.clearAgyOutput();
const clearedLogs = domElements['agy-terminal-output'].textContent;

window.visualizer.closeAgyModal();
const modalClosingOpacity = domElements['agy-modal-backdrop'].classList.contains('opacity-0');

const results = {
  hasFacadeExports, modalOpen, targetBadgeText,
  promptHasTaskId: promptVal.includes('TASK-0042'),
  previewHasSkipPerms: previewVal.includes('--dangerously-skip-permissions'),
  healthPromptHasScript: healthPromptVal.includes('health_check.py'),
  contPreviewHasCFlag: contPreviewVal.includes('-c -p'),
  drawerBtnHasLaunch: drawerBtnHtml.includes('Launch AGY'),
  clearedLogs: clearedLogs.includes('Logs cleared'),
  modalClosingOpacity,
};
console.log(JSON.stringify(results));
"""

    test_script = template_script.replace("__CLIENT_BUNDLE__", client_bundle)
    proc = subprocess.run([node_bin], input=test_script, capture_output=True, text=True)
    assert proc.returncode == 0, f"Error in frontdoor client test: {proc.stderr}"
    res = json.loads(proc.stdout)
    expected = {
        "hasFacadeExports": True,
        "modalOpen": True,
        "targetBadgeText": "TASK-0042",
        "promptHasTaskId": True,
        "previewHasSkipPerms": True,
        "healthPromptHasScript": True,
        "contPreviewHasCFlag": True,
        "drawerBtnHasLaunch": True,
        "clearedLogs": True,
        "modalClosingOpacity": True,
    }
    for k, v in expected.items():
        assert res[k] == v, f"{k}: expected {v}, got {res[k]}"
