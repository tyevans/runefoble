#!/usr/bin/env bash
# PRD Creation, Maintenance, and Task Decomposition Pipeline
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

COMMAND="${1:-audit}"

case "$COMMAND" in
  audit)
    python3 -m tools.prd_pipeline.cli audit
    ;;
  create)
    shift
    if [ "$#" -lt 1 ]; then
      echo "Usage: $0 create --title \"<Title>\" [--persona \"<Persona>\"] [--bc \"<BC>\"] [--summary \"<Summary>\"]"
      exit 1
    fi
    python3 -m tools.prd_pipeline.cli create "$@"
    ;;
  decompose)
    shift
    if [ "$#" -lt 1 ]; then
      echo "Usage: $0 decompose --prd <PRD-ID> [--plan-only]"
      exit 1
    fi
    python3 -m tools.prd_pipeline.cli decompose "$@"
    ;;
  decompose-all)
    shift
    python3 -m tools.prd_pipeline.cli decompose-all "$@"
    ;;
  sync)
    python3 -m tools.prd_pipeline.cli sync
    ;;
  agent)
    shift
    if [ "$#" -lt 1 ]; then
      echo "Usage: $0 agent <PRD-ID>"
      exit 1
    fi
    PRD_ID="$1"
    echo "==> Generating decomposition instructions for $PRD_ID..."
    PROMPT=$(python3 -m tools.prd_pipeline.cli prompt --prd "$PRD_ID")
    echo "==> Invoking Antigravity agy to perform semantic decomposition..."
    agy --dangerously-skip-permissions -p "$PROMPT"
    ;;
  prompt)
    shift
    python3 -m tools.prd_pipeline.cli prompt "$@"
    ;;
  *)
    # Pass arbitrary args directly to CLI
    python3 -m tools.prd_pipeline.cli "$@"
    ;;
esac
