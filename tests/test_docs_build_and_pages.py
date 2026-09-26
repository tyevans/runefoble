"""Blackbox tests for Zensical documentation build, project visualizer integration, and GitHub Pages CI/CD."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
SITE_DIR = REPO_ROOT / "site"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "deploy-pages.yml"
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
ZENSICAL_TOML = REPO_ROOT / "zensical.toml"


def test_zensical_configuration():
    """Verify zensical.toml is valid, configured for GitHub Pages, and all nav items exist."""
    assert ZENSICAL_TOML.exists(), "zensical.toml must exist in repo root"

    with open(ZENSICAL_TOML, "rb") as f:
        config = tomllib.load(f)

    project = config.get("project", {})
    assert project.get("site_name") == "Runefoble"
    assert "tyevans.github.io/runefoble" in project.get("site_url", "")
    assert project.get("repo_name") == "tyevans/runefoble"

    # Verify nav entries point to valid files
    nav = project.get("nav", [])
    assert len(nav) >= 6

    def verify_nav_items(items):
        for item in items:
            if isinstance(item, dict):
                for _label, target in item.items():
                    if isinstance(target, str):
                        target_file = DOCS_DIR / target
                        assert target_file.exists(), (
                            f"Nav target {target} does not exist at {target_file}"
                        )
                    elif isinstance(target, list):
                        verify_nav_items(target)
            elif isinstance(item, list):
                verify_nav_items(item)

    verify_nav_items(nav)


def test_docs_site_generation_and_visualizer_integration():
    """Verify build generates full HTML documentation, search index, and embedded visualizer."""
    if not SITE_DIR.exists() or not (SITE_DIR / "visualizer" / "index.html").exists():
        import subprocess
        import sys

        subprocess.run([sys.executable, "scripts/build_docs.py"], cwd=str(REPO_ROOT), check=True)

    assert SITE_DIR.exists(), "site/ directory should exist after build"

    # 1. Main index
    index_html = SITE_DIR / "index.html"
    assert index_html.exists()
    content = index_html.read_text(encoding="utf-8")
    assert "Runefoble" in content

    # 2. Project visualizer embedded page
    proj_vis_index = SITE_DIR / "project-visualizer" / "index.html"
    assert proj_vis_index.exists()
    proj_content = proj_vis_index.read_text(encoding="utf-8")
    assert "visualizer" in proj_content

    # 3. Standalone visualizer web application at /visualizer/index.html
    visualizer_html = SITE_DIR / "visualizer" / "index.html"
    assert visualizer_html.exists()
    vis_size_kb = visualizer_html.stat().st_size / 1024
    assert vis_size_kb > 300, (
        f"Standalone visualizer bundle should be >300KB, got {vis_size_kb:.1f}KB"
    )
    vis_content = visualizer_html.read_text(encoding="utf-8")
    assert "Runefoble Project Content Visualizer" in vis_content

    # 4. Parity file /project-visualizer.html
    assert (SITE_DIR / "project-visualizer.html").exists()

    # 5. Raw structured JSON data
    json_path = SITE_DIR / "project-data.json"
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "tasks" in data
    assert "adrs" in data
    assert "edges" in data
    assert len(data["tasks"]) > 50
    assert len(data["edges"]) > 100

    # 6. Search index
    search_json = SITE_DIR / "search.json"
    assert search_json.exists()
    search_data = json.loads(search_json.read_text(encoding="utf-8"))
    assert "items" in search_data
    assert len(search_data["items"]) > 100

    # 7. GitHub Pages nojekyll marker
    assert (SITE_DIR / ".nojekyll").exists()


def test_github_pages_deploy_workflow():
    """Verify GitHub Pages deployment workflow triggers on main and uses official pages actions."""
    assert WORKFLOW_PATH.exists()
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        wf = yaml.safe_load(f)

    # Verify triggers
    triggers = wf.get("on") or wf.get(True, {})
    push_branches = triggers.get("push", {}).get("branches", [])
    assert "main" in push_branches
    assert "workflow_dispatch" in triggers

    # Verify permissions
    permissions = wf.get("permissions", {})
    assert permissions.get("pages") == "write"
    assert permissions.get("id-token") == "write"
    assert permissions.get("contents") == "read"

    # Verify concurrency
    concurrency = wf.get("concurrency", {})
    assert concurrency.get("group") == "pages"

    # Verify steps
    deploy_job = wf.get("jobs", {}).get("deploy", {})
    steps = deploy_job.get("steps", [])
    step_runs_and_uses = [s.get("uses", "") + s.get("run", "") for s in steps]

    assert any("actions/configure-pages" in s for s in step_runs_and_uses)
    assert any("actions/upload-pages-artifact" in s for s in step_runs_and_uses)
    assert any("actions/deploy-pages" in s for s in step_runs_and_uses)
    assert any("make docs-build" in s for s in step_runs_and_uses)


def test_ci_workflow_includes_docs_verification():
    """Verify CI workflow verifies docs and visualizer on every pull request."""
    assert CI_WORKFLOW_PATH.exists()
    with open(CI_WORKFLOW_PATH, encoding="utf-8") as f:
        ci_wf = yaml.safe_load(f)

    jobs = ci_wf.get("jobs", {})
    assert "docs-verification" in jobs
    docs_job = jobs["docs-verification"]
    steps = docs_job.get("steps", [])
    step_commands = [s.get("run", "") for s in steps]
    assert any("make docs-build" in cmd for cmd in step_commands)
