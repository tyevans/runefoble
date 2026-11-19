#!/usr/bin/env python3
"""Runefoble Unified Local Development Orchestrator (`make dev`).

Starts the API Gateway, optional background inference worker, and hot-reloading Vite frontend
concurrently with health check gating and clean signal handling. The implementation lives in
`scripts/dev_orchestrator/`. This file is the command entry point.

Governed by ADR-0004, ADR-0010, and ADR-0013. Part of TASK-0352.
"""

from __future__ import annotations

import sys
from pathlib import Path

# A script run by path puts scripts/ on sys.path, not the repository root. Add the root, so the
# `scripts` package resolves the same way as under pytest.
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.dev_orchestrator.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
