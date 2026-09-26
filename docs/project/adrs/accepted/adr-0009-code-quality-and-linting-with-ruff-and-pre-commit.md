# ADR-0009: Code Quality, Static Analysis, and Linting via Ruff and Pre-commit

## Context

A multi-package monorepo with multiple contributors and autonomous AI agents requires instantaneous, automated style and lint enforcement to prevent formatting noise and anti-patterns from polluting commit logs.

## Decision

We adopt **Ruff** as our unified Python linter and formatter, backed by **pre-commit** hooks:

1. **Ruff as All-in-One Engine**:
   - Replaces Black, Flake8, isort, and bandit.
   - Configured in root `pyproject.toml` with target version Python 3.13.
   - Rules enforced:
     - `E`, `W` (pycodestyle errors/warnings)
     - `F` (Pyflakes)
     - `I` (isort import sorting)
     - `B` (flake8-bugbear)
     - `C4` (flake8-comprehensions)
     - `UP` (pyupgrade)
     - `SIM` (flake8-simplify)
2. **Git Pre-Commit Automation**:
   - `.pre-commit-config.yaml` runs on every `git commit`.
   - Checks include: `ruff`, `ruff-format`, trailing whitespace removal, YAML validation, and merge conflict marker checks.
3. **Zero-Warning Tolerance**:
   - CI runs `ruff check .` with exit-on-error.

## Consequences

- Lint checks execute in milliseconds across the entire monorepo.
- Code style is uniform across all services and libraries.
- Autonomous agent work is formatted identically to human contributions.
