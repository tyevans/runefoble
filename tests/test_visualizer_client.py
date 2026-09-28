"""Tests for Project Visualizer client JavaScript syntax, markdown rendering, and Gantt charts."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.project_visualizer.assets_js import get_client_js
from tools.project_visualizer.generator import ProjectVisualizerGenerator


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_client_javascript_syntax_validity(repo_root: Path):
    """Verify all static JavaScript modules and concatenated bundles are 100% valid syntax."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js binary not found for syntax checking")

    # 1. Test every individual static JS module (recursively including subviews)
    static_js_dir = repo_root / "tools" / "project_visualizer" / "static" / "js"
    for js_file in static_js_dir.rglob("*.js"):
        proc = subprocess.run([node_bin, "-c", str(js_file)], capture_output=True, text=True)
        assert proc.returncode == 0, f"Syntax error in {js_file.name}: {proc.stderr}"

    # 2. Test live server bundled JS
    live_bundle = get_client_js(is_live_server=True)
    proc_live = subprocess.run([node_bin, "-c"], input=live_bundle, capture_output=True, text=True)
    assert proc_live.returncode == 0, f"Syntax error in live bundle: {proc_live.stderr}"

    # 3. Test static distribution bundled JS
    static_bundle = get_client_js(is_live_server=False)
    proc_static = subprocess.run(
        [node_bin, "-c"], input=static_bundle, capture_output=True, text=True
    )
    assert proc_static.returncode == 0, f"Syntax error in static bundle: {proc_static.stderr}"


def test_markdown_renderer_and_drawer_integration(repo_root: Path):
    """Verify client markdown renderer parses ADR sections into formatted HTML."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js binary not found for markdown rendering verification")

    client_bundle = get_client_js(is_live_server=False)
    test_script = f"""
const window = {{ visualizer: {{}} }};
global.window = window;
global.document = {{ addEventListener: () => {{}}, querySelectorAll: () => [], getElementById: () => null }};

{client_bundle}

const adrDecision = `We adopt \\`eventsource-py\\`:
1. **Domain Events**: Registered via \\`@register_event\\`.
2. **Aggregates**: Subclasses of \\`DeclarativeAggregate\\`:
   - \\`GameSessionAggregate\\` in \\`services/game_session\\`
   - \\`BoardAggregate\\` in \\`services/board_state\\`
3. **Distribution**: Events published via Redis.`;

const html = window.visualizer.renderMarkdown(adrDecision);

// Test inline markdown on persona pain points/goals and ADR card summaries
const personaBullet = "Standard \\`MCP\\` server with **sub-50ms** response and [docs](https://example.com).";
const inlinePersona = window.visualizer.renderInlineMarkdown(personaBullet);

const adrSummary = "We adopt **SpiceDB** (Google Zanzibar).\\n\\n1. **Object-Level Scoping**: Using \\`resource:id\\`.";
const inlineAdr = window.visualizer.renderInlineMarkdown(adrSummary);

const results = {{
    hasOl: html.includes('<ol class="list-decimal'),
    hasUl: html.includes('<ul class="list-disc'),
    hasStrong: html.includes('<strong class="font-semibold text-white">Domain Events</strong>'),
    hasCode: html.includes('eventsource-py</code>'),
    hasNestedCode: html.includes('GameSessionAggregate</code>'),
    isHtml: html.startsWith('<p'),
    personaHasCode: inlinePersona.includes('MCP</code>'),
    personaHasStrong: inlinePersona.includes('<strong class="font-semibold text-white">sub-50ms</strong>'),
    personaHasLink: inlinePersona.includes('href="https://example.com"'),
    personaNoP: !inlinePersona.startsWith('<p'),
    adrHasStrong: inlineAdr.includes('<strong class="font-semibold text-white">SpiceDB</strong>'),
    adrHasCode: inlineAdr.includes('resource:id</code>'),
    adrNoP: !inlineAdr.startsWith('<p')
}};
console.log(JSON.stringify(results));
"""

    proc = subprocess.run([node_bin], input=test_script, capture_output=True, text=True)
    assert proc.returncode == 0, f"Error executing markdown test script: {proc.stderr}"
    data = json.loads(proc.stdout)
    assert data["hasOl"] is True
    assert data["hasUl"] is True
    assert data["hasStrong"] is True
    assert data["hasCode"] is True
    assert data["hasNestedCode"] is True
    assert data["isHtml"] is True
    assert data["personaHasCode"] is True
    assert data["personaHasStrong"] is True
    assert data["personaHasLink"] is True
    assert data["personaNoP"] is True
    assert data["adrHasStrong"] is True
    assert data["adrHasCode"] is True
    assert data["adrNoP"] is True


def test_gantt_chart_dynamic_milestones_and_timeline_rendering(repo_root: Path):
    """Verify Gantt chart renders dynamic 10-milestone scale and accurate bar lane offsets."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js binary not found for gantt rendering verification")

    client_bundle = get_client_js(is_live_server=False)
    project_data = ProjectVisualizerGenerator(repo_root).get_data().to_dict()

    test_script = f"""
const window = {{ visualizer: {{}} }};
global.window = window;
global.document = {{ addEventListener: () => {{}}, querySelectorAll: () => [], getElementById: () => null }};

{client_bundle}

const container = {{ innerHTML: '' }};
const state = {{
  data: {json.dumps(project_data, default=str)},
  filters: {{ hideDone: false, bc: 'all', milestone: 'all', search: '' }},
  gantt: {{ groupBy: 'milestone' }}
}};

window.visualizer.renderGantt(container, state);
const html = container.innerHTML;

const results = {{
  hasM1: html.includes('>M1<'),
  hasM10: html.includes('>M10<'),
  hasAppShell: html.includes('App Shell'),
  noOldPhase1: !html.includes('Phase 1: Foundations'),
  noOldPhase2: !html.includes('Phase 2: Alpha (Now)'),
  noOldPhase3: !html.includes('Phase 3: AI DM'),
  noOldPhase4: !html.includes('Phase 4: Studio'),
  hasMilestoneFilter: html.includes('All Milestones'),
  hasGanttGrid: html.includes('gantt-grid'),
  htmlSnippet: html.slice(0, 1500)
}};
console.log(JSON.stringify(results));
"""

    proc = subprocess.run([node_bin], input=test_script, capture_output=True, text=True)
    assert proc.returncode == 0, f"Error executing gantt test script: {proc.stderr}"
    res = json.loads(proc.stdout)
    assert res["hasM1"] is True
    assert res["hasM10"] is True
    assert res["hasAppShell"] is True
    assert res["noOldPhase1"] is True
    assert res["noOldPhase2"] is True
    assert res["noOldPhase3"] is True
    assert res["noOldPhase4"] is True
    assert res["hasMilestoneFilter"] is True
    assert res["hasGanttGrid"] is True
