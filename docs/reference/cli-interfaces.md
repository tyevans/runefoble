# Reference: CLI and Tool Interfaces

## Makefile Targets

| Target | Description |
|---|---|
| `make help` | Displays all available developer commands |
| `make setup` | Installs Python UV workspace dependencies and frontend packages |
| `make health-check` | Gate. Runs `spec-ops health` (file length <500 lines in `libs/`, `services/`, `gateway/`, `frontend/`, `tests/`, `scripts/`, `e2e/`, `tools/`; numbering; backlog state) `spec-ops schema check` (frontmatter and Markdown grammar in `docs/project/`); then `scripts/check_backlog_links.py` (dead links in refined and proposed tasks, stale PRD links, complete-record body status, unresolved cited paths (a folder holding only `__pycache__` counts as missing), missing governance keys; all must be zero). It also prints curation warnings for the refined buffer band (6 to 12) and for refined tasks that wait on incomplete tasks. Warnings never fail the gate |
| `make install-spec-ops` | Installs the pinned spec-ops CLI with `uv tool install`. The pin is the `SPEC_OPS_SOURCE` variable in the `Makefile`, the only pin source. CI and AGENTS.md use this target. A command-line override is ignored |
| `make clean-worktrees` | Removes merged, idle, clean git worktrees and their local branches (`ARGS="--dry-run"`). It skips a worktree that a process uses as its working directory. When the process table (`/proc`, or `--proc-dir`) is absent, it reports `cannot verify` and skips every worktree. `--all` also removes unmerged worktrees. `--force` also removes dirty worktrees. It exits with code 1 when a removal or `git worktree prune` fails |
| `make backlog-worker` | Runs autonomous backlog execution engine (`ARGS="--drain --concurrency 2"`). Local tool, kept. See the parity record below |
| `make visualize-project` | Launches dynamic docs/project content visualizer web application on port 8787. Local tool, kept. See the parity record below |
| `make visualize-project-build` | Builds standalone HTML bundle (`dist/project-visualizer.html`). Local tool, kept. See the parity record below |
| `make docs-build` | Compiles documentation static site via Zensical with integrated project visualizer. A failed build step stops the build with a non-zero exit code. On Linux, a full inotify watch limit makes the build fail. See "Raise the inotify watch limit" in `docs/tutorials/01-local-development-setup.md` |
| `make docs-serve` | Builds the docs with `scripts/build_docs.py`, then serves the site with `zensical serve` on port 8000 (the Zensical default, verified by running the target) |
| `make cluster-up` | Launches local Kind Kubernetes cluster with port mapping and Traefik |
| `make cluster-down` | Deletes the local Kind cluster and every volume in it (PostgreSQL, Silo, and Redis data) |
| `make install-tools` | Checks that `kind`, `uv`, `pnpm`, `helm`, and `docker` are on `PATH`. Installs `kind` v0.27.0 into `~/.local/bin` when `kind` is missing |
| `make images` | Builds every service image (`runefoble/<service>:0.1.0`). Python services use `deployments/docker/python-service.Dockerfile` and load into the `runefoble-local` Kind cluster. The Node `audience-studio` image uses `services/audience_studio/Dockerfile` (Node 22, pnpm 11.22.0 from the frozen lockfile, runs `dist/index.js` as the `node` user on port 8010) and is loaded the same way. The App Shell `frontend` image uses `frontend/Dockerfile`. Build it from the repository root (`docker build -f frontend/Dockerfile .`). Its context comes from `frontend/Dockerfile.dockerignore`, which keeps the pnpm workspace and `services/*/ui`. It serves the built App Shell with nginx on port 80 and is loaded the same way. |
| `make images-push` | Hosted path (TASK-0960). Builds the same images as `make images`, tags them `<IMAGE_REGISTRY>/runefoble/<name>:0.1.0`, pushes each one, and records the pushed digest in `deployments/helm/runefoble/values.images.yaml` with `scripts/record_image_digests.py`. Requires `IMAGE_REGISTRY` (for example `make images-push IMAGE_REGISTRY=registry.example.com/team`). The target fails before any build when the variable is empty. It does not load images into Kind and does not run `docker login`: log in to the registry first. Use `make -n images-push` for a dry run. Pass the resulting file with `-f` after the hosted values file (see [hosted-profile.md](hosted-profile.md)). |
| `make helm-lint` | Validates Helm chart syntax. `make lint` runs it as a prerequisite |
| `make helm-template` | Renders and inspects Kubernetes manifests |
| `make helm-check-event-store` | Runs `scripts/check_helm_event_store.py`. Finds aggregate owners in Python (`AggregateRepository`) and TypeScript (`AudienceEventRepository`) non-test source. Fails when an owner has no PostgreSQL event store in the Helm chart |
| `make helm-deploy` | Deploys the full Runefoble stack to the active Kubernetes cluster. It adds `values.local.yaml` when that file exists. It does not pass `--wait`. `helm upgrade --install --wait` is supported: the chart has no Helm hook that waits for an app pod, and the bucket and schema Jobs are plain Jobs (TASK-0933). A Kind run with `--wait` is verified by the orchestrator (TASK-0964). This is the Kind developer path. A hosted release does not use this target. Use `helm upgrade --install` with your hosted values file. See [hosted-profile.md](hosted-profile.md) |
| `make dev` | Runs API Gateway and Vite frontend concurrently with health check gating and clean signal handling. Requires a reachable Redis (`RUNEFOBLE_REDIS_URL`, default `redis://localhost:6379/0`). The orchestrator port-forwards `svc/runefoble-redis` from Kind when needed, and exits with code 1 when no Redis answers. Every child process stops when `make dev` stops, including after `SIGKILL` on Linux |
| `make dev-frontend` | Runs the Vite frontend development server |
| `make dev-storybook` | Runs the Storybook component studio on port 6006 |
| `make dev-api` | Runs the API Gateway locally |
| `make dev-worker` | Runs AI inference worker locally |
| `make deploy-remote-worker` | Syncs the workspace with rsync to the remote GPU host set in the Makefile and runs `uv sync` there |
| `make dev-audience-studio` | Runs Audience Studio from TypeScript source with reload (`pnpm run dev` in `services/audience_studio`, which runs `tsx watch src/index.ts`). Listens on port 8010 and serves `GET /healthz`. Needs `RUNEFOBLE_ZITADEL_ISSUER`, `RUNEFOBLE_ZITADEL_AUDIENCE`, `RUNEFOBLE_SPICEDB_PRESHARED_KEY`, `RUNEFOBLE_SPICEDB_ENDPOINT`, `RUNEFOBLE_DATABASE_URL`, and `RUNEFOBLE_REDIS_URL`. Start-up fails without them. `NODE_ENV=test` does not select an in-memory store and does not make the SpiceDB key optional. |
| `make test` | Runs the Python test suite in two phases, then builds the frontend. Phase 1 runs all tests except `serial` tests in parallel with pytest-xdist (`-n $(PYTEST_WORKERS)`, default 8). Phase 2 runs the `serial` tests one at a time. A `serial` test checks wall-clock time or starts a browser, so heavy parallel load makes it fail. `SERIAL_MODULES` in the repository root `conftest.py` lists these modules (also tests that start a service process with PostgreSQL and Redis). The per-test timeout is 300 seconds (`[tool.pytest.ini_options]`). A test that exceeds it fails with a timeout error |
| `make test-authz-live` | Runs the live SpiceDB authorization suite (`pytest -m authz_live`) with `RUNEFOBLE_REQUIRE_LIVE_SPICEDB=1`. Needs Docker. The run fails if Docker is missing |
| `make test-entrypoints` | Runs `tests/test_entrypoints.py`. Covers developer entrypoints, CLI tools, and microservice start-up |
| `make test-gateway` | Runs `uv run pytest gateway/api`, the gateway API test package in `gateway/api/tests/`. Its tests use the root shared helpers. The canned-payload behaviour guard is `tests/test_canned_payload_guard.py` and runs in `make test` |
| `make test-property` | Runs the Hypothesis property tests in `tests/test_properties.py` |
| `make test-mutation` | Runs `mutmut` on the core domain modules (`source_paths` in `[tool.mutmut]`), then prints the mutants that were not killed. Policy: the target fails when `mutmut run` fails or when one or more mutants survive. Mutants with other statuses (for example `no tests`) are printed but do not fail the target |
| `make test-e2e` | Runs `bddgen`, then the headless Playwright BDD suite. Passes `ARGS` to `playwright test` |
| `make test-e2e-ui` | Runs `bddgen`, then opens the Playwright UI mode for live debugging. Passes `ARGS` to `playwright test` |
| `make e2e-lore-up` | Scales `deployment/campaign-lore` on Kind to 1. Waits for the rollout and until the gateway `/healthz` reports `campaign_lore` as `operational` |
| `make e2e-lore-down` | Scales `deployment/campaign-lore` on Kind to 0. Waits until the gateway `/healthz` reports `campaign_lore` as `unreachable` |
| `make e2e-game-session-up` | The same as `make e2e-lore-up`, for `deployment/game-session` and `game_session` |
| `make e2e-game-session-down` | The same as `make e2e-lore-down`, for `deployment/game-session` and `game_session` |
| `make lint` | Runs Ruff lint and format checks, the hex colour gate (`scripts/check_hex_literals.py`, baseline `scripts/hex_baseline.json`), the Lit template gate (`scripts/check_lit_templates.py`: kebab-case attributes with no matching `attribute:`, and SVG fragments in `html` templates), mypy on the inference worker and the MCP gateway, frontend and e2e typechecks, and `helm lint` |
| `make lint-fix` | Runs `ruff check --fix` and `ruff format` on the repository |
| `make pre-commit` | Runs every pre-commit hook on all files with `uv run pre-commit run --all-files` |
| `make test-bdd` | Typechecks `e2e/` (`pnpm run e2e:typecheck`), runs the e2e guard unit tests (`node --test e2e/unit/*.test.ts`), fails on unused Playwright BDD step definitions (`uv run python scripts/check_e2e_unused_steps.py`), and runs `bddgen`. Does not launch browsers |
| `make build` | Produces production frontend bundle and static Storybook documentation |
| `make check-ui-manifests` | Fails when a service UI manifest is missing or invalid (ADR-0013, ADR-0015) |
| `make voice-model-cache` | Downloads the faster-whisper model set by `VOICE_MODEL_SIZE` (default `tiny.en`) into `.cache/voice-models`, then copies it into the running voice-agent pod. Needs the `faster-whisper` engine: the chart creates no model cache for `whisper-cpp` |
| `make prd-audit` | Audits PRD decomposition status, buffer health (6 to 12 refined tasks), and detects epic proposed tasks by the scope rule in the decomposition how-to. Local tool, kept. See the parity record below |
| `make prd-decompose` | Decomposes PRDs into ADR spikes and vertical slices (`ARGS="--prd PRD-0014"`). Local tool, kept. See the parity record below |
| `make prd-create` | Scaffolds a new PRD document with frontmatter and registers it. Local tool, kept. See the parity record below |
| `make prd-sync` | Synchronizes PRD, User Story, and Backlog Priority registries. Local tool, kept. See the parity record below |

## spec-ops Parity Record (TASK-0700)

A local tool stays only when this record names a reason. A local tool is deleted only after a
comparison on the same tree shows parity. The comparisons ran on 2026-11-17 with the spec-ops
pin in `Makefile` (`SPEC_OPS_SOURCE`). Each run used the same checkout.

| Local target | spec-ops command | Comparison run | Result | Decision |
|---|---|---|---|---|
| `make prd-audit` | `spec-ops prd audit` | Ran both on one tree. Local: 24 PRDs, 96 ready tasks, PRD-0014 under-decomposed, 200 oversized proposed tasks. spec-ops: 25 PRDs, 1 undecomposed, 96 ready tasks | Differs. spec-ops counts `PRIORITY.md` as a PRD and reports it as undecomposed. spec-ops has no per-task scope check | Keep local |
| `make prd-decompose` | `spec-ops prd decompose` | Not run. The command writes into `docs/project/` | No result | Keep local. Parity not shown |
| `make prd-create` | `spec-ops prd create` | Not run. The command writes a new PRD file | No result | Keep local. Parity not shown |
| `make prd-sync` | None. `spec-ops prd` has no `sync` action | Checked `spec-ops prd --help` | No equivalent | Keep local |
| `make backlog-worker` | `spec-ops queue next`, `spec-ops queue tree`, `spec-ops worker --auto --dry-run` | Local `list` and spec-ops `queue tree` both show the same READY set. `queue next` returns the first READY task. Local `--dry-run` prints only the header and exits, and it runs `recover_stale_tasks()` before the check. spec-ops `worker --auto --dry-run` wrote `claimed_by` and `branch` into a refined task file, dropped two frontmatter fields, and created a lease directory | Dry-run parity fails. spec-ops dry-run is not read-only. Execution parity not run | Keep local |
| `make visualize-project` | `spec-ops visualizer --serve` | Not run. Serve output was not compared | No result | Keep local. Parity not shown |
| `make visualize-project-build` | `spec-ops visualizer --build` | Ran both into `/tmp`. Local: exit 0, 4.77 MB bundle. spec-ops: exit 1, `Exported visualizer bundle size (8083743 bytes) exceeds 5242880 byte (5MB) limit`, and the file was still written | Fails on this tree. The spec-ops bundle is over its own size cap | Keep local |

Tasks 0235, 0291, 0328, 0335 and 0346 stay open. They wait on the visualizer parity check.

## Automation Runner Scripts

| Script | Purpose |
|---|---|
| `./scripts/dev_server.py` | Unified local development orchestrator (requires Redis; see `make dev`) running gateway, Vite frontend, and optional AI inference worker concurrently |
| `make clean-worktrees` | Runs `scripts/cleanup_worktrees.py`. Audits and removes merged, idle worktrees, deletes their branches, and prunes records (`ARGS="--dry-run"`). It fails closed: when it cannot read the process table, it removes nothing |
| `./scripts/curate-backlog.sh` | Invokes the `backlog-curator` skill for JIT backlog triage and roadmap alignment |
| `make backlog-worker` | Orchestrates autonomous end-to-end task execution, worktrees, PRs, and CI watching (`ARGS="--concurrency 3"`) |
| `make visualize-project` | Starts dynamic project content visualizer web application on port 8787 |
| `./scripts/decompose-prds.sh` | PRD pipeline runner to audit, scaffold, decompose into vertical slices/spikes, and sync |
