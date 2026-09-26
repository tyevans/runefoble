# ADR-0010: Continuous Integration and Deployment Gates via GitHub Actions

## Context

To protect the `main` branch from regressions, every pull request and push must be verified against identical build and test gates before integration.

## Decision

We establish an automated **GitHub Actions CI Workflow** (`.github/workflows/ci.yml`) enforcing four parallel quality stages:

1. **Python Quality Matrix**:
   - `ruff check .` and `ruff format --check .`
   - `uv run pytest` running unit and integration tests across all bounded contexts.
   - `uv run pytest tests/test_properties.py` running Hypothesis property tests.
2. **Frontend Quality Matrix**:
   - TypeScript compilation (`pnpm exec tsc --noEmit`).
   - Production Vite build (`pnpm run build`).
   - Static Storybook build (`pnpm run build-storybook`).
3. **Infrastructure Quality Matrix**:
   - `helm lint deployments/helm/runefoble`
   - `helm template runefoble deployments/helm/runefoble`
4. **Zanzibar Schema Validation**:
   - SpiceDB schema syntax check on `libs/runefoble_auth/schema/runefoble.zed`.

## Consequences

- Broken builds and regressions are blocked automatically before code can be merged into `main`.
- Developer environments, local Kind setups, and cloud runners execute identical Makefile commands.
