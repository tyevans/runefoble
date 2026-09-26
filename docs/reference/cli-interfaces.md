# Reference: CLI and Tool Interfaces

## Makefile Targets

| Target | Description |
|---|---|
| `make help` | Displays all available developer commands |
| `make setup` | Installs Python UV workspace dependencies and frontend packages |
| `make health-check` | Audits codebase line counts (<500 lines) and backlog ready buffer |
| `make backlog-worker` | Runs autonomous backlog execution engine (`ARGS="--drain --concurrency 2"`) |
| `make visualize-project` | Launches dynamic docs/project content visualizer web application on port 8787 |
| `make visualize-project-build` | Builds standalone HTML bundle (`dist/project-visualizer.html`) |
| `make docs-build` | Compiles documentation static site via Zensical with integrated project visualizer |
| `make docs-serve` | Serves documentation site locally with live preview on port 8000 |
| `make cluster-up` | Launches local Kind Kubernetes cluster with port mapping and Traefik |
| `make cluster-down` | Deletes the local Kind cluster |
| `make helm-lint` | Validates Helm chart syntax |
| `make helm-template` | Renders and inspects Kubernetes manifests |
| `make helm-deploy` | Deploys the full Runefoble stack to the active Kubernetes cluster |
| `make dev-frontend` | Runs the Vite frontend development server |
| `make dev-storybook` | Runs the Storybook component studio on port 6006 |
| `make dev-api` | Runs the API Gateway locally |
| `make test` | Executes the Python test suite and builds the frontend |
| `make lint` | Runs typechecking and Helm chart linter |
| `make build` | Produces production frontend bundle and static Storybook documentation |

## Automation Runner Scripts

| Script | Purpose |
|---|---|
| `./scripts/health_check.py` | Standalone Python health inspection auditing line count invariants and buffer drift |
| `./scripts/curate-backlog.sh` | Invokes the `backlog-curator` skill for JIT backlog triage and roadmap alignment |
| `./scripts/run-backlog-engine.sh` | Orchestrates autonomous end-to-end task execution, worktrees, PRs, and CI watching |
| `./scripts/visualize-project.sh` | Starts dynamic project content visualizer web application on port 8787 |
