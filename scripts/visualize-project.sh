#!/usr/bin/env bash
set -euo pipefail

# Runefoble Project Content Visualizer runner
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PORT="${1:-8787}"

echo "Starting Runefoble Project Content Visualizer on port $PORT..."
python3 -m tools.project_visualizer.cli serve --root "$REPO_ROOT" --port "$PORT"
