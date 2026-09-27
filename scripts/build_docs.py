#!/usr/bin/env python3
"""Runefoble Documentation & Project Visualizer Site Builder.

Builds the standalone project visualizer bundle, synchronizes operating manual
documentation, compiles the Zensical documentation static site, integrates
the interactive visualizer into the static distribution, and prepares artifacts
for deployment to GitHub Pages.
"""

from __future__ import annotations

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

    # Ensure inotify watch exhaustion on Linux workstations does not silently abort static site builds.
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


def sync_changelog() -> None:
    """Synchronize docs/changelog.md from root CHANGELOG.md."""
    changelog_path = ROOT_DIR / "CHANGELOG.md"
    target_path = DOCS_DIR / "changelog.md"

    if not changelog_path.exists():
        return

    content = changelog_path.read_text(encoding="utf-8")
    target_path.write_text(content, encoding="utf-8")
    print(f"📖 Synchronized {target_path.relative_to(ROOT_DIR)} from CHANGELOG.md")


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


def build_storybook(env: dict[str, str]) -> Path | None:
    """Build static Storybook component studio if pnpm is available, or locate existing static build."""
    frontend_dir = ROOT_DIR / "frontend"
    storybook_static = frontend_dir / "storybook-static"
    pnpm = shutil.which("pnpm")

    if pnpm and (frontend_dir / "package.json").exists():
        print("🎨 Building static Storybook component studio...")
        cmd = [pnpm, "exec", "storybook", "build", "--disable-telemetry", "--quiet"]
        try:
            subprocess.run(cmd, cwd=str(frontend_dir), check=True, env=env)
        except Exception as e:
            print(f"⚠️ Warning: Storybook build failed: {e}")

    if storybook_static.exists() and (storybook_static / "index.html").exists():
        return storybook_static
    return None


def integrate_artifacts(
    visualizer_bundle: Path, storybook_bundle: Path | None, env: dict[str, str]
) -> None:
    """Embed standalone visualizer, Storybook studio, and project JSON data into the generated site directory."""
    print("🔗 Integrating visualizer, Storybook, and datasets into documentation site...")
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

    # 4. Integrate Storybook static distribution if built
    if storybook_bundle and storybook_bundle.exists():
        print("🎨 Embedding Storybook component catalog into site/storybook/...")
        dest_storybook = SITE_DIR / "storybook"
        if dest_storybook.exists():
            shutil.rmtree(dest_storybook)
        shutil.copytree(storybook_bundle, dest_storybook)

    # 5. Create .nojekyll for GitHub Pages compatibility
    (SITE_DIR / ".nojekyll").touch()

    # 5. Normalize any escaping relative links generated by static site generator
    for html_file in SITE_DIR.glob("**/*.html"):
        content = html_file.read_text(encoding="utf-8")
        rel = html_file.relative_to(SITE_DIR)
        depth = len(rel.parts) - 1

        def replace_link(match: re.Match[str], file_depth: int = depth) -> str:
            attr = match.group(1)
            target = match.group(2)
            if target.startswith(("http://", "https://", "mailto:", "#", "data:")):
                return match.group(0)
            dot_count = len(target.split("../")) - 1 if target.startswith("../") else 0
            if dot_count > file_depth:
                excess = dot_count - file_depth
                corrected = target[3 * excess :]
                return f'{attr}="{corrected}"'
            return match.group(0)

        new_content = re.sub(r'(\b(?:href|src))=["\']([^"\']+)["\']', replace_link, content)
        if new_content != content:
            html_file.write_text(new_content, encoding="utf-8")


def print_summary() -> None:
    """Print build completion statistics."""
    html_count = len(list(SITE_DIR.glob("**/*.html")))
    search_index = SITE_DIR / "search.json"
    index_size_kb = search_index.stat().st_size / 1024 if search_index.exists() else 0
    storybook_index = SITE_DIR / "storybook" / "index.html"
    storybook_status = "Included" if storybook_index.exists() else "Omitted"

    print("\n" + "=" * 60)
    print("🎉 Runefoble Documentation & Visualizer Build Succeeded!")
    print(f"📁 Site Output Directory: {SITE_DIR}")
    print(f"📄 Total HTML Pages:     {html_count}")
    print(f"🔍 Search Index Size:    {index_size_kb:.1f} KB")
    print(f"🌐 Visualizer Route:     {SITE_DIR / 'visualizer' / 'index.html'}")
    print(f"🎨 Storybook Studio:     {storybook_status} ({SITE_DIR / 'storybook' / 'index.html'})")
    print("=" * 60 + "\n")


def main() -> None:
    env = os.environ.copy()
    check_and_prepare_inotify_env(env)
    sync_operating_manual()
    sync_changelog()
    visualizer_bundle = build_visualizer(env)
    storybook_bundle = build_storybook(env)
    build_zensical_site(env)
    integrate_artifacts(visualizer_bundle, storybook_bundle, env)
    print_summary()


if __name__ == "__main__":
    main()
