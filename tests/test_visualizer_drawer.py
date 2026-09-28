"""Tests for Project Visualizer Drawer subviews decomposition and frontdoor interactions."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.project_visualizer.assets_js import get_client_js


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_drawer_module_decomposition_architecture(repo_root: Path):
    """Verify drawer subviews architecture, file counts, and Hard Invariant 6 line limits."""
    drawer_dir = repo_root / "tools" / "project_visualizer" / "static" / "js" / "drawer"
    assert drawer_dir.is_dir(), "drawer/ subdirectory must exist"

    expected_modules = {
        "task_card.js": 100,
        "adr_card.js": 90,
        "prd_card.js": 90,
        "persona_card.js": 80,
        "controller.js": 80,
    }

    # Verify all expected modules exist and verify target and hard limits
    for mod_name, target_limit in expected_modules.items():
        mod_path = drawer_dir / mod_name
        assert mod_path.is_file(), f"Expected drawer subview {mod_name} does not exist"
        lines = len(mod_path.read_text(encoding="utf-8").splitlines())
        assert lines < target_limit, f"{mod_name} must be < {target_limit} lines, got {lines}"
        assert lines < 120, f"{mod_name} strictly < 120 lines per Hard Invariant 6, got {lines}"

    # Verify zero files in drawer directory exceed 150 lines
    for js_file in drawer_dir.glob("*.js"):
        lines = len(js_file.read_text(encoding="utf-8").splitlines())
        assert lines <= 150, f"{js_file.name} exceeds 150 lines: {lines}"

    # Verify coordinator drawer.js line count
    drawer_js = repo_root / "tools" / "project_visualizer" / "static" / "js" / "drawer.js"
    assert drawer_js.is_file(), "drawer.js coordinator must exist"
    coord_lines = len(drawer_js.read_text(encoding="utf-8").splitlines())
    assert coord_lines < 80, f"drawer.js coordinator must be < 80 lines, got {coord_lines}"
    assert coord_lines < 120, f"drawer.js coordinator strictly < 120 lines, got {coord_lines}"


def test_drawer_subviews_and_controller_frontdoor(repo_root: Path):
    """Frontdoor verification of drawer opening, card subviews rendering, and action bridges."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js binary not found for frontdoor drawer verification")

    client_bundle = get_client_js(is_live_server=True)

    test_script = f"""
class MockElement {{
  constructor(id) {{
    this.id = id;
    this.innerHTML = '';
    this.textContent = '';
    this.classList = {{
      classes: new Set(),
      add: (c) => this.classList.classes.add(c),
      remove: (c) => this.classList.classes.delete(c),
      contains: (c) => this.classList.classes.has(c),
    }};
  }}
}}

const elements = {{
  'drawer': new MockElement('drawer'),
  'drawer-backdrop': new MockElement('drawer-backdrop'),
  'drawer-type-badge': new MockElement('drawer-type-badge'),
  'drawer-id': new MockElement('drawer-id'),
  'drawer-body': new MockElement('drawer-body'),
  'drawer-filepath': new MockElement('drawer-filepath'),
}};
elements['drawer'].classList.add('translate-x-full');
elements['drawer-backdrop'].classList.add('hidden', 'opacity-0');

const copiedTexts = [];
const clipboardMock = {{
  writeText: async (text) => {{
    copiedTexts.push(text);
    return Promise.resolve();
  }}
}};
try {{
  Object.defineProperty(global.navigator, 'clipboard', {{ value: clipboardMock, configurable: true }});
}} catch (e) {{
  global.navigator = {{ clipboard: clipboardMock }};
}}

const window = {{ visualizer: {{}}, navigator: {{ clipboard: clipboardMock }} }};
global.window = window;
global.document = {{
  addEventListener: () => {{}},
  querySelectorAll: () => [],
  getElementById: (id) => elements[id] || null,
}};

{client_bundle}

// Seed project test data
window.visualizer.state.data = {{
  tasks: [
    {{
      id: 'TASK-0042',
      title: 'Tactile Token Kinematics',
      status: 'Refined',
      target_bc: 'board_state',
      target_release: '0.2.0',
      file_path: 'docs/project/backlog/refined/0042-tactile-token-kinematics.md',
      governing_adrs: ['ADR-0004'],
      dependencies: ['TASK-0001'],
      prs: ['PR #42'],
      commits: [{{ hash: 'a1b2c3d', date: '2026-09-26', author: 'Evelyn', subject: 'feat: add kinematic tokens' }}],
      microfrontends: ['runefoble-tactile-board'],
      raw_markdown: '## Task 0042 Specification',
    }}
  ],
  stories: [
    {{
      id: 'US-0010',
      title: 'Move Token Tactilely',
      persona: 'Player',
      as_a: 'Tabletop Player',
      i_want: 'to move tokens smoothly',
      so_that: 'the game feel is tactile',
      file_path: 'docs/project/user_stories/US-0010.md',
      acceptance_criteria: ['Snap to 5-foot grid', 'Trajectory preview'],
      raw_markdown: '## Story 0010 Content',
    }}
  ],
  prds: [
    {{
      id: 'PRD-0005',
      title: 'Tactile Board Engine',
      status: 'Accepted',
      file_path: 'docs/project/product/accepted/prd-0005.md',
      problem_statement: 'Tokens feel unresponsive without physical kinematics.',
      outcomes: ['Sub-16ms move latency', 'Fluid animations'],
    }}
  ],
  adrs: [
    {{
      id: 'ADR-0004',
      title: 'Lit Web Components and Storybook',
      status: 'Accepted',
      domain: 'Frontend',
      date: '2026-09-20',
      file_path: 'docs/project/adrs/0004-lit-web-components.md',
      context: 'We require modular, encapsulated components.',
      decision: 'Adopt Lit Web Components in Storybook.',
      consequences: 'Encapsulated styling via Shadow DOM.',
      implementing_tasks: ['TASK-0042'],
      raw_markdown: '## ADR 0004 Record',
    }}
  ],
  personas: [
    {{
      id: 'evelyn',
      name: 'Evelyn',
      role: 'Dungeon Master',
      quote: 'I want storytelling without administrative friction.',
      avatar_color: '#8B5CF6',
      file_path: 'docs/project/user_stories/personas.md',
      pain_points: ['Tracking initiative and conditions manually'],
      goals: ['Immersive tabletop encounters'],
      key_features: ['Watcher AI', 'Board Sync'],
    }}
  ]
}};

// 1. Verify Task Card subview & openDrawer
window.visualizer.openDrawer('TASK-0042');
const taskBadge = elements['drawer-type-badge'].textContent;
const taskId = elements['drawer-id'].textContent;
const taskBody = elements['drawer-body'].innerHTML;
const taskDrawerOpen = !elements['drawer'].classList.contains('translate-x-full');
const hasTaskStatus = taskBody.includes('Refined');
const hasTargetBc = taskBody.includes('board_state');
const hasTargetRelease = taskBody.includes('Release 0.2.0');
const hasCommit = taskBody.includes('a1b2c3d');
const hasPr = taskBody.includes('PR #42');
const hasAdrBtn = taskBody.includes("openDrawer('ADR-0004')");
const hasAgyAction = taskBody.includes('Launch AGY') || window.visualizer.renderTaskDrawerActions !== undefined;

// 2. Verify closeDrawer
window.visualizer.closeDrawer();
const taskDrawerClosed = elements['drawer'].classList.contains('translate-x-full');
const selectedNodeAfterClose = window.visualizer.state.selectedNode;

// 3. Verify ADR Card subview
window.visualizer.openDrawer('ADR-0004');
const adrBadge = elements['drawer-type-badge'].textContent;
const adrBody = elements['drawer-body'].innerHTML;
const hasAdrContext = adrBody.includes('modular, encapsulated components');
const hasAdrDecision = adrBody.includes('Adopt Lit Web Components');
const hasAdrImplTask = adrBody.includes("openDrawer('TASK-0042')");

// 4. Verify PRD Card subview
window.visualizer.openDrawer('PRD-0005');
const prdBadge = elements['drawer-type-badge'].textContent;
const prdBody = elements['drawer-body'].innerHTML;
const hasPrdProblem = prdBody.includes('unresponsive without physical kinematics');
const hasPrdOutcome = prdBody.includes('Sub-16ms move latency');

// 5. Verify Story Card subview
window.visualizer.openDrawer('US-0010');
const storyBadge = elements['drawer-type-badge'].textContent;
const storyBody = elements['drawer-body'].innerHTML;
const hasStoryAsA = storyBody.includes('Tabletop Player');
const hasStoryCriteria = storyBody.includes('Snap to 5-foot grid');

// 6. Verify Persona Card subview
window.visualizer.openDrawer('evelyn');
const personaBadge = elements['drawer-type-badge'].textContent;
const personaBody = elements['drawer-body'].innerHTML;
const hasPersonaQuote = personaBody.includes('storytelling without administrative friction');
const hasPersonaGoal = personaBody.includes('Immersive tabletop encounters');

// 7. Verify copyDrawerFilepath
window.visualizer.copyDrawerFilepath();

// 8. Verify window.app bridges
const hasAppOpen = typeof window.app.openDrawer === 'function';
const hasAppClose = typeof window.app.closeDrawer === 'function';
const hasAppCopy = typeof window.app.copyDrawerFilepath === 'function';

const results = {{
  taskBadge,
  taskId,
  taskDrawerOpen,
  hasTaskStatus,
  hasTargetBc,
  hasTargetRelease,
  hasCommit,
  hasPr,
  hasAdrBtn,
  hasAgyAction,
  taskDrawerClosed,
  selectedNodeAfterClose: selectedNodeAfterClose === null,
  adrBadge,
  hasAdrContext,
  hasAdrDecision,
  hasAdrImplTask,
  prdBadge,
  hasPrdProblem,
  hasPrdOutcome,
  storyBadge,
  hasStoryAsA,
  hasStoryCriteria,
  personaBadge,
  hasPersonaQuote,
  hasPersonaGoal,
  copiedTexts,
  hasAppOpen,
  hasAppClose,
  hasAppCopy,
}};
console.log(JSON.stringify(results));
"""

    proc = subprocess.run([node_bin], input=test_script, capture_output=True, text=True)
    assert proc.returncode == 0, f"Error running drawer test script: {proc.stderr}"
    res = json.loads(proc.stdout)

    assert res["taskBadge"] == "TASK"
    assert res["taskId"] == "TASK-0042"
    assert res["taskDrawerOpen"] is True
    assert res["hasTaskStatus"] is True
    assert res["hasTargetBc"] is True
    assert res["hasTargetRelease"] is True
    assert res["hasCommit"] is True
    assert res["hasPr"] is True
    assert res["hasAdrBtn"] is True
    assert res["hasAgyAction"] is True
    assert res["taskDrawerClosed"] is True
    assert res["selectedNodeAfterClose"] is True

    assert res["adrBadge"] == "ADR"
    assert res["hasAdrContext"] is True
    assert res["hasAdrDecision"] is True
    assert res["hasAdrImplTask"] is True

    assert res["prdBadge"] == "PRD"
    assert res["hasPrdProblem"] is True
    assert res["hasPrdOutcome"] is True

    assert res["storyBadge"] == "STORY"
    assert res["hasStoryAsA"] is True
    assert res["hasStoryCriteria"] is True

    assert res["personaBadge"] == "PERSONA"
    assert res["hasPersonaQuote"] is True
    assert res["hasPersonaGoal"] is True

    assert "docs/project/user_stories/personas.md" in res["copiedTexts"]
    assert res["hasAppOpen"] is True
    assert res["hasAppClose"] is True
    assert res["hasAppCopy"] is True
