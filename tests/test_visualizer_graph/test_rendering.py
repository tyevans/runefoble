"""Tests for visualizer client graph rendering, layout switching, and line invariants."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.project_visualizer.assets_js import get_client_js
from tools.project_visualizer.generator import ProjectVisualizerGenerator


def test_graph_modular_decomposition_and_line_invariants(repo_root: Path):
    """Verify TASK-0217 decomposition: submodules exist, strictly < 150 lines, and meet targets."""
    graph_js = repo_root / "tools" / "project_visualizer" / "static" / "js" / "graph.js"
    graph_dir = repo_root / "tools" / "project_visualizer" / "static" / "js" / "graph"

    assert graph_js.exists(), "graph.js orchestrator must exist"
    assert graph_dir.is_dir(), "graph/ submodule directory must exist"

    targets = {"simulation.js": 90, "nodes.js": 110, "links.js": 100, "zoom.js": 80}
    for filename, max_lines in targets.items():
        module_file = graph_dir / filename
        assert module_file.exists(), f"Submodule {filename} must exist"
        lines = len(module_file.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{filename} has {lines} lines (target < {max_lines})"
        assert lines < 150, f"{filename} has {lines} lines (limit < 150)"

    graph_lines = len(graph_js.read_text(encoding="utf-8").splitlines())
    assert graph_lines < 70 and graph_lines < 150
    for f in graph_dir.glob("*.js"):
        assert len(f.read_text(encoding="utf-8").splitlines()) < 150


def test_graph_renderer_and_interactions_via_node(repo_root: Path):
    """Verify frontdoor graph rendering, layout switching, node clicks, and search via Node.js."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js binary not found for frontdoor graph rendering verification")

    client_bundle = get_client_js(is_live_server=False)
    project_data = ProjectVisualizerGenerator(repo_root).get_data().to_dict()

    test_script = f"""
const elements = new Map();
function makeElement(id) {{
  const el = {{
    id, style: {{}},
    classList: {{
      classes: new Set(),
      add(c) {{ this.classes.add(c); }},
      remove(c) {{ this.classes.delete(c); }},
      toggle(c, f) {{ if (f === undefined) f = !this.classes.has(c); if (f) this.classes.add(c); else this.classes.delete(c); return f; }}
    }},
    setAttribute(k, v) {{ this[k] = v; }}, getAttribute(k) {{ return this[k]; }},
    clientWidth: 1200, clientHeight: 800,
    getBoundingClientRect() {{ return {{ left: 0, top: 0, width: 1200, height: 800 }}; }}
  }};
  elements.set(id, el);
  return el;
}}
const window = {{ visualizer: {{}} }};
global.window = window;
global.requestAnimationFrame = (cb) => setTimeout(cb, 16);
global.cancelAnimationFrame = (id) => clearTimeout(id);
global.document = {{
  addEventListener: () => {{}}, querySelectorAll: () => [],
  getElementById: (id) => elements.get(id) || makeElement(id)
}};

{client_bundle}

const container = {{ innerHTML: '' }};
const state = {{
  data: {json.dumps(project_data, default=str)},
  filters: {{ hideDone: false, bc: 'all', search: '' }}
}};
window.visualizer.renderGraph(container, state);
const html = container.innerHTML;

window.visualizer.switchGraphLayout('flow');
const flowActive = window.visualizer.graphState.activeLayout === 'flow';
window.visualizer.switchGraphLayout('radial');
const radialActive = window.visualizer.graphState.activeLayout === 'radial';
window.visualizer.switchGraphLayout('network');
const networkActive = window.visualizer.graphState.activeLayout === 'network';
window.visualizer.toggleGraphPhysics();
const paused = !window.visualizer.graphState.physicsRunning;
window.visualizer.toggleGraphPhysics();
const running = window.visualizer.graphState.physicsRunning;
window.visualizer.reheatGraphPhysics();

const firstNode = window.visualizer.graphState.nodes[0];
if (firstNode) window.visualizer.handleGraphNodeClick(firstNode.id);
const selected = window.visualizer.graphState.selectedId === (firstNode ? firstNode.id : null);
window.visualizer.clearNodeHighlights();
const cleared = window.visualizer.graphState.selectedId === null;
if (firstNode) window.visualizer.focusNodeFromSearch(firstNode.id);
const searchFocused = window.visualizer.graphState.zoom === 1.35;

console.log(JSON.stringify({{
  hasSvg: html.includes('<svg id="graph-svg"'),
  hasMarkerDefs: html.includes('id="arrow"'),
  hasPanLayer: html.includes('id="graph-pan-layer"'),
  hasMinimap: html.includes('id="graph-minimap"'),
  hasStatPill: html.includes('id="graph-stat-pill"'),
  flowActive, radialActive, networkActive, paused, running,
  selected, cleared, searchFocused
}}));
"""
    proc = subprocess.run([node_bin], input=test_script, capture_output=True, text=True)
    assert proc.returncode == 0, f"Error in node script: {proc.stderr}"
    res = json.loads(proc.stdout)
    assert all(res.values()), f"Failed assertions: {[k for k, v in res.items() if not v]}"
