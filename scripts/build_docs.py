#!/usr/bin/env python3
"""Runefoble Documentation & Project Visualizer Site Builder.

Builds the standalone project visualizer bundle, synchronizes operating manual
documentation, compiles the Zensical documentation static site, integrates
the interactive visualizer into the static distribution, and prepares artifacts
for deployment to GitHub Pages.
"""

from __future__ import annotations

import ctypes
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
DIST_DIR = ROOT_DIR / "dist"
SITE_DIR = ROOT_DIR / "site"
CACHE_DIR = ROOT_DIR / ".cache"


def check_and_prepare_inotify_env(env: dict[str, str]) -> None:
    """Ensure inotify watch exhaustion on local development workstations does not break static builds."""
    if sys.platform != "linux":
        return

    # Test if inotify is currently operational
    try:
        libc = ctypes.CDLL(None)
        if hasattr(libc, "inotify_init") and hasattr(libc, "inotify_add_watch"):
            fd = libc.inotify_init()
            if fd >= 0:
                wd = libc.inotify_add_watch(fd, b"/tmp", 1)
                libc.close(fd)
                if wd >= 0:
                    return  # Inotify watches are healthy
    except Exception:
        pass

    # Inotify watch limit reached. Compile and preload lightweight shim.
    shim_c = ROOT_DIR / "scripts" / "fake_inotify.c"
    if not shim_c.exists():
        return

    shim_so = ROOT_DIR / "scripts" / "fake_inotify.so"

    if not shim_so.exists() or shim_so.stat().st_mtime < shim_c.stat().st_mtime:
        gcc = shutil.which("gcc")
        if gcc:
            cmd = [gcc, "-shared", "-fPIC", "-O2", "-o", str(shim_so), str(shim_c), "-ldl"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"⚠️ Warning: Could not compile inotify shim: {result.stderr}")
                return

    if shim_so.exists():
        existing_preload = env.get("LD_PRELOAD", "")
        env["LD_PRELOAD"] = f"{shim_so}:{existing_preload}".strip(":")


def sync_operating_manual() -> None:
    """Synchronize docs/operating-manual.md from root AGENTS.md, adjusting internal links."""
    agents_path = ROOT_DIR / "AGENTS.md"
    target_path = DOCS_DIR / "operating-manual.md"

    if not agents_path.exists():
        return

    content = agents_path.read_text(encoding="utf-8")
    # Adjust relative paths from root-relative (docs/...) to docs-relative (...)
    content = re.sub(r"\]\(docs/", "](", content)
    # Remove redundant self-references if any
    target_path.write_text(content, encoding="utf-8")
    print(f"📖 Synchronized {target_path.relative_to(ROOT_DIR)} from AGENTS.md")


def build_visualizer(env: dict[str, str]) -> Path:
    """Build standalone single-file HTML bundle for docs/project visualizer."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    out_file = DIST_DIR / "project-visualizer.html"
    print("🔨 Building standalone Project Visualizer bundle...")
    cmd = [
        sys.executable,
        "-m",
        "tools.project_visualizer.cli",
        "build",
        "--out",
        str(out_file),
    ]
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True, env=env)
    return out_file


def build_zensical_site(env: dict[str, str]) -> None:
    """Execute Zensical build to generate static documentation HTML and search index."""
    print("📚 Building documentation site via Zensical...")
    cmd = ["uv", "run", "zensical", "build", "--clean"]
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True, env=env)


def integrate_artifacts(visualizer_bundle: Path, env: dict[str, str]) -> None:
    """Embed standalone visualizer and project JSON data into the generated site directory."""
    print("🔗 Integrating visualizer and datasets into documentation site...")
    visualizer_dir = SITE_DIR / "visualizer"
    visualizer_dir.mkdir(parents=True, exist_ok=True)

    # 1. Standalone visualizer at /visualizer/index.html
    dest_visualizer = visualizer_dir / "index.html"
    shutil.copy2(visualizer_bundle, dest_visualizer)

    # 2. Also keep /project-visualizer.html for direct link parity
    shutil.copy2(visualizer_bundle, SITE_DIR / "project-visualizer.html")

    # 3. Export project content graph JSON to /project-data.json
    json_dest = SITE_DIR / "project-data.json"
    cmd = [
        sys.executable,
        "-m",
        "tools.project_visualizer.cli",
        "export-json",
        "--out",
        str(json_dest),
    ]
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True, env=env)

    # 4. Create .nojekyll for GitHub Pages compatibility
    (SITE_DIR / ".nojekyll").touch()


def print_summary() -> None:
    """Print build completion statistics."""
    html_count = len(list(SITE_DIR.glob("**/*.html")))
    search_index = SITE_DIR / "search.json"
    index_size_kb = search_index.stat().st_size / 1024 if search_index.exists() else 0

    print("\n" + "=" * 60)
    print("🎉 Runefoble Documentation & Visualizer Build Succeeded!")
    print(f"📁 Site Output Directory: {SITE_DIR}")
    print(f"📄 Total HTML Pages:     {html_count}")
    print(f"🔍 Search Index Size:    {index_size_kb:.1f} KB")
    print(f"🌐 Visualizer Route:     {SITE_DIR / 'visualizer' / 'index.html'}")
    print("=" * 60 + "\n")


def main() -> None:
    env = os.environ.copy()
    check_and_prepare_inotify_env(env)
    sync_operating_manual()
    visualizer_bundle = build_visualizer(env)
    build_zensical_site(env)
    integrate_artifacts(visualizer_bundle, env)
    print_summary()


if __name__ == "__main__":
    main()
