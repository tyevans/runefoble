#!/usr/bin/env bash
# Curate Runefoble backlog with JIT refinement, refactoring scanning, and roadmap alignment
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "==> Running Codebase & Backlog Health Check..."
python3 scripts/health_check.py

# Check git status
if [ -n "$(git status --porcelain)" ]; then
  if [[ "${1:-}" != "--force" ]]; then
    echo ""
    echo "⚠️ Warning: Working tree is dirty. Backlog curation modifies backlog files."
    echo "Please commit/stash your changes, or run with: $0 --force"
    exit 1
  fi
fi

echo ""
echo "==> Triggering Antigravity Backlog Curator..."
agy --dangerously-skip-permissions -p \
  "Activate the 'backlog-curator' skill in .agents/skills/backlog-curator/SKILL.md:
1. Review files approaching 500 lines and propose refactoring tasks in docs/project/backlog/proposed/ if needed.
2. Inspect docs/project/backlog/ROADMAP.md Milestone 2 and ensure foundational enablers are prioritized.
3. Check the ready buffer in docs/project/backlog/refined/. If < 10 items, JIT-refine the top proposed/enabler item (citing ADRs, testable blackbox DoD). Keep buffer to ~10 items.
4. Synchronize docs/project/backlog/PRIORITY.md."
