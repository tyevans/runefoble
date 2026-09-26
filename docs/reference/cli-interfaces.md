# Reference: CLI and Tool Interfaces

## Makefile Targets

| Target | Description |
|---|---|
| `make help` | Displays all available developer commands |
| `make setup` | Installs Python UV workspace dependencies and frontend packages |
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
