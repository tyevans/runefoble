"""Tests for Project Visualizer graph construction and traceability."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.project_visualizer.assets_js import get_client_js
from tools.project_visualizer.generator import ProjectVisualizerGenerator
from tools.project_visualizer.graph import ProjectGraphBuilder
from tools.project_visualizer.parser import (
    ProjectParser,
    build_traceability_graph,
    scan_project,
)
from tools.project_visualizer.parsers import GraphBuilder


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_graph_builder_and_traceability_edges(repo_root: Path):
    parser = ProjectParser(repo_root)
    data = parser.parse_all()
    builder = ProjectGraphBuilder(data)
    builder.build()

    assert len(data.edges) > 100

    # Check edge relations
    relations = {e.relation for e in data.edges}
    assert "desires" in relations
    assert "specifies" in relations
    assert "governed_by" in relations
    assert "deploys_to" in relations

    # Check health metrics
    m = data.metrics
    assert m.total_adrs >= 13
    assert m.total_prds >= 12
    assert m.total_stories >= 40
    assert m.total_tasks >= 50
    assert m.completed_tasks >= 30
    assert m.refined_tasks >= 0
    assert m.ready_buffer_status in ["optimal", "over_buffered", "under_buffered"]


def test_graph_builder_facade_compatibility(repo_root: Path):
    scanned_data = scan_project(repo_root)
    built_data = build_traceability_graph(scanned_data)
    assert len(built_data.edges) > 100
    assert built_data.metrics.total_tasks > 0

    builder_instance = GraphBuilder(scanned_data)
    assert builder_instance.build() is built_data


def test_all_prds_have_stories_and_tasks_support(repo_root: Path):
    parser = ProjectParser(repo_root)
    data = parser.parse_all(force=True)
    builder = ProjectGraphBuilder(data)
    builder.build()

    assert len(data.prds) >= 16
    for prd in data.prds:
        assert len(prd.linked_stories) >= 1, f"PRD {prd.id} ({prd.title}) has 0 linked user stories"
        assert len(prd.implementing_tasks) >= 1, (
            f"PRD {prd.id} ({prd.title}) has 0 implementing tasks"
        )

    assert len(data.metrics.orphaned_stories) == 0, (
        f"Found orphaned stories: {data.metrics.orphaned_stories}"
    )


def test_html_bundle_contains_graph_and_gantt(repo_root: Path, tmp_path: Path):
    generator = ProjectVisualizerGenerator(repo_root)
    out_file = tmp_path / "test-full-visualizer.html"
    result = generator.build_file(out_file)

    content = result.read_text(encoding="utf-8")
    assert "Relationship Graph" in content
    assert "Gantt & Timeline" in content
    assert "Hide Done" in content
    assert "Git Commits & Pull Requests" in content
    assert "ForceSimulation" in content
    assert "graph-minimap" in content
    assert "edge-active-flow" in content
    assert "focus-ripple" in content
    assert "switchGraphLayout" in content


def test_graph_visualizer_zoom_and_minimap_bundle(repo_root: Path, tmp_path: Path):
    generator = ProjectVisualizerGenerator(repo_root)
    out_file = tmp_path / "test-zoom-minimap.html"
    result = generator.build_file(out_file)

    content = result.read_text(encoding="utf-8")
    # Verify focal mouse zoom anchoring
    assert "zoomGraph(factor, focalX, focalY)" in content or "zoomGraph" in content
    assert "focalX" in content
    assert "focalY" in content
    # Verify minimap real-time node updates and interaction
    assert "mm-node-" in content
    assert "updateMinimap" in content
    assert "moveCameraToMinimapPoint" in content
    assert "minimap-view-rect" in content
    assert "isDraggingMinimap" in content


def test_graph_modular_decomposition_and_line_invariants(repo_root: Path):
    """Verify TASK-0217 decomposition: submodules exist, strictly < 150 lines, and meet targets."""
    graph_js = repo_root / "tools" / "project_visualizer" / "static" / "js" / "graph.js"
    graph_dir = repo_root / "tools" / "project_visualizer" / "static" / "js" / "graph"

    assert graph_js.exists(), "graph.js orchestrator must exist"
    assert graph_dir.is_dir(), "graph/ submodule directory must exist"

    # Specific targets from TASK-0217
    targets = {
        "simulation.js": 90,
        "nodes.js": 110,
        "links.js": 100,
        "zoom.js": 80,
    }

    for filename, max_lines in targets.items():
        module_file = graph_dir / filename
        assert module_file.exists(), f"Submodule {filename} must exist under static/js/graph/"
        lines = len(module_file.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{filename} has {lines} lines, exceeding target < {max_lines}"
        assert lines < 150, (
            f"{filename} has {lines} lines, violating Hard Invariant 6 / DoD (< 150)"
        )

    # Check graph.js orchestrator (< 70 lines target, < 150 limit)
    graph_lines = len(graph_js.read_text(encoding="utf-8").splitlines())
    assert graph_lines < 70, f"graph.js has {graph_lines} lines, exceeding target < 70"
    assert graph_lines < 150, (
        f"graph.js has {graph_lines} lines, violating Hard Invariant 6 / DoD (< 150)"
    )

    # Invariant: Zero files in static/js/graph/ exceed 150 lines
    for f in graph_dir.glob("*.js"):
        lines = len(f.read_text(encoding="utf-8").splitlines())
        assert lines < 150, f"File {f.name} in static/js/graph/ exceeds 150 lines ({lines})"


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
    id,
    style: {{}},
    classList: {{
      classes: new Set(),
      add(c) {{ this.classes.add(c); }},
      remove(c) {{ this.classes.delete(c); }},
      toggle(c, force) {{ if (force === undefined) force = !this.classes.has(c); if (force) this.classes.add(c); else this.classes.delete(c); return force; }}
    }},
    setAttribute(k, v) {{ this[k] = v; }},
    getAttribute(k) {{ return this[k]; }},
    clientWidth: 1200,
    clientHeight: 800,
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
  addEventListener: () => {{}},
  querySelectorAll: () => [],
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

// Verify submodules were orchestrated
const hasSvg = html.includes('<svg id="graph-svg"');
const hasMarkerDefs = html.includes('id="arrow"');
const hasPanLayer = html.includes('id="graph-pan-layer"');
const hasMinimap = html.includes('id="graph-minimap"');
const hasStatPill = html.includes('id="graph-stat-pill"');

// Test interaction functions
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

// Test node selection / highlighting
const firstNode = window.visualizer.graphState.nodes[0];
if (firstNode) {{
  window.visualizer.handleGraphNodeClick(firstNode.id);
}}
const selected = window.visualizer.graphState.selectedId === (firstNode ? firstNode.id : null);

window.visualizer.clearNodeHighlights();
const cleared = window.visualizer.graphState.selectedId === null;

// Test focus from search
if (firstNode) {{
  window.visualizer.focusNodeFromSearch(firstNode.id);
}}
const searchFocused = window.visualizer.graphState.zoom === 1.35;

const results = {{
  hasSvg, hasMarkerDefs, hasPanLayer, hasMinimap, hasStatPill,
  flowActive, radialActive, networkActive, paused, running,
  selected, cleared, searchFocused
}};
console.log(JSON.stringify(results));
"""

    proc = subprocess.run([node_bin], input=test_script, capture_output=True, text=True)
    assert proc.returncode == 0, f"Error in node script: {proc.stderr}"
    res = json.loads(proc.stdout)
    assert res["hasSvg"] is True
    assert res["hasMarkerDefs"] is True
    assert res["hasPanLayer"] is True
    assert res["hasMinimap"] is True
    assert res["hasStatPill"] is True
    assert res["flowActive"] is True
    assert res["radialActive"] is True
    assert res["networkActive"] is True
    assert res["paused"] is True
    assert res["running"] is True
    assert res["selected"] is True
    assert res["cleared"] is True
    assert res["searchFocused"] is True
