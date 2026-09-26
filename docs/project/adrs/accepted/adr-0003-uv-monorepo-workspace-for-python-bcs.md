# ADR-0003: UV Monorepo Workspace for Python Bounded Contexts

## Context

The backend consists of multiple bounded contexts:
- Shared libraries: `libs/runefoble_platform`, `libs/runefoble_auth`, `libs/runefoble_events`.
- Microservices: `services/the_watcher`, `services/game_session`, `services/board_state`, `services/character_sheet`, `services/voice_agent`.
- Gateways: `gateway/api`, `gateway/mcp`.

Managing multiple separate repositories or multi-tool virtual environments creates high development friction, lockfile drift, and slow CI feedback loops.

## Decision

We manage all Python bounded contexts in a single monorepo using **`uv` workspaces**:

1. **Workspace Root**: The root `pyproject.toml` defines `[tool.uv.workspace]` declaring `libs/*`, `services/*`, and `gateway/*`.
2. **Deterministic Locking**: A single unified `uv.lock` coordinates all workspace dependencies with near-instant resolution.
3. **Local Inter-Package Links**: Libraries are consumed across services via `{ workspace = true }` without manual packaging or private package index overhead.
4. **Isolated Bounded Contexts**: Each BC maintains its own `pyproject.toml` with strict explicit dependencies.

## Consequences

- Dependency synchronization across all BCs takes under one second.
- Refactoring shared models in `libs/` immediately propagates to downstream services.
- Test suites run seamlessly across all packages from the root directory.
