# Reference: CLI and Tool Interfaces

## Makefile Targets

| Target | Description |
|---|---|
| `make help` | Displays all available developer commands |
| `make setup` | Installs Python UV workspace dependencies and frontend packages |
| `make health-check` | Audits codebase line counts (<500 lines) and backlog ready buffer |
| `make clean-worktrees` | Cleans up merged and stale git worktrees safely (`ARGS="--dry-run"`) |
| `make backlog-worker` | Runs autonomous backlog execution engine (`ARGS="--drain --concurrency 2"`) |
| `make visualize-project` | Launches dynamic docs/project content visualizer web application on port 8787 |
| `make visualize-project-build` | Builds standalone HTML bundle (`dist/project-visualizer.html`) |
| `make docs-build` | Compiles documentation static site via Zensical with integrated project visualizer |
| `make docs-serve` | Builds the docs with `scripts/build_docs.py`, then serves the site with `zensical serve` on port 8000 (the Zensical default, verified by running the target) |
| `make cluster-up` | Launches local Kind Kubernetes cluster with port mapping and Traefik |
| `make cluster-down` | Deletes the local Kind cluster |
| `make install-tools` | Checks that `kind`, `uv`, `pnpm`, `helm`, and `docker` are on `PATH`. Installs `kind` v0.27.0 into `~/.local/bin` when `kind` is missing |
| `make images` | Builds every service image (`runefoble/<service>:0.1.0`). Python services use `deployments/docker/python-service.Dockerfile` and load into the `runefoble-local` Kind cluster. The Node `audience-studio` image uses `services/audience_studio/Dockerfile` (Node 22, pnpm 11.22.0 from the frozen lockfile, runs `dist/index.js` as the `node` user on port 8010) and is loaded the same way. |
| `make helm-lint` | Validates Helm chart syntax |
| `make helm-template` | Renders and inspects Kubernetes manifests |
| `make helm-check-event-store` | Runs `scripts/check_helm_event_store.py`. Fails when a service that owns aggregates has no PostgreSQL event store in the Helm chart |
| `make helm-deploy` | Deploys the full Runefoble stack to the active Kubernetes cluster |
| `make dev` | Runs API Gateway and Vite frontend concurrently with health check gating and clean signal handling |
| `make dev-frontend` | Runs the Vite frontend development server |
| `make dev-storybook` | Runs the Storybook component studio on port 6006 |
| `make dev-api` | Runs the API Gateway locally |
| `make dev-worker` | Runs AI inference worker locally |
| `make deploy-remote-worker` | Syncs the workspace with rsync to the remote GPU host set in the Makefile and runs `uv sync` there |
| `make dev-audience-studio` | Runs Audience Studio from TypeScript source with reload (`pnpm run dev` in `services/audience_studio`, which runs `tsx watch src/index.ts`). Listens on port 8010 and serves `GET /healthz`. Needs `RUNEFOBLE_ZITADEL_ISSUER`, `RUNEFOBLE_ZITADEL_AUDIENCE`, `RUNEFOBLE_SPICEDB_PRESHARED_KEY`, and either `RUNEFOBLE_DATABASE_URL` plus `REDIS_URL`, or `NODE_ENV=test`. Start-up fails without them. |
| `make test` | Executes the Python test suite (`uv run pytest`, default per-test timeout of 300 seconds from `[tool.pytest.ini_options]`; a test that exceeds it fails with a timeout error) and builds the frontend |
| `make test-entrypoints` | Runs `tests/test_entrypoints.py`. Covers developer entrypoints, CLI tools, and microservice start-up |
| `make test-property` | Runs the Hypothesis property tests in `tests/test_properties.py` |
| `make test-mutation` | Runs `mutmut` on the core domain modules and prints the results. A failed run does not stop the target |
| `make test-e2e` | Runs `bddgen`, then the headless Playwright BDD suite. Passes `ARGS` to `playwright test` |
| `make test-e2e-ui` | Runs `bddgen`, then opens the Playwright UI mode for live debugging. Passes `ARGS` to `playwright test` |
| `make lint` | Runs Ruff lint and format checks, mypy on the inference worker, frontend and e2e typechecks, and `helm lint` |
| `make lint-fix` | Runs `ruff check --fix` and `ruff format` on the repository |
| `make pre-commit` | Runs every pre-commit hook on all files with `uv run pre-commit run --all-files` |
| `make test-bdd` | Typechecks `e2e/` (`pnpm run e2e:typecheck`), fails on unused Playwright BDD step definitions (`uv run python scripts/check_e2e_unused_steps.py`), and runs `bddgen`. Does not launch browsers |
| `make build` | Produces production frontend bundle and static Storybook documentation |
| `make voice-model-cache` | Downloads the faster-whisper model set by `VOICE_MODEL_SIZE` (default `tiny.en`) into `.cache/voice-models`, then copies it into the running voice-agent pod |
| `make prd-audit` | Audits PRD decomposition status, buffer health, and detects oversized tasks |
| `make prd-decompose` | Decomposes PRDs into ADR spikes and vertical slices (`ARGS="--prd PRD-0014"`) |
| `make prd-create` | Scaffolds a new PRD document with frontmatter and registers it |
| `make prd-sync` | Synchronizes PRD, User Story, and Backlog Priority registries |

## Automation Runner Scripts

| Script | Purpose |
|---|---|
| `./scripts/health_check.py` | Standalone Python health inspection auditing line count invariants and buffer drift |
| `./scripts/dev_server.py` | Unified local development orchestrator running gateway, Vite frontend, and optional AI inference worker concurrently |
| `./scripts/cleanup-worktrees.sh` | Audits and removes merged git worktrees, cleans up branches, and prunes records |
| `./scripts/curate-backlog.sh` | Invokes the `backlog-curator` skill for JIT backlog triage and roadmap alignment |
| `./scripts/run-backlog-engine.sh` | Orchestrates autonomous end-to-end task execution, worktrees, PRs, and CI watching |
| `./scripts/visualize-project.sh` | Starts dynamic project content visualizer web application on port 8787 |
| `./scripts/decompose-prds.sh` | PRD pipeline runner to audit, scaffold, decompose into vertical slices/spikes, and sync |
