# Tutorial 01: Local Development Setup with Kind and Helm

## Objective
In this tutorial, you will spin up a local development environment for Runefoble using Kind (Kubernetes in Docker), install the Traefik ingress controller, and verify the stack using Helm.

## Prerequisites
- Docker running locally
- `uv` (>= 0.8.0)
- `node` (>= 20) and `pnpm`
- `helm` (>= 3.10)
- `kind` (Kubernetes in Docker)
- `make`

## Step 1: Install Dependencies
Run the unified setup command to configure the Python UV workspace and frontend packages:
```bash
make setup
```

## Step 2: Spin Up the Kind Kubernetes Cluster
Run:
```bash
make cluster-up
```
This command:
1. Reads `deployments/kind/cluster-config.yaml`.
2. Creates a local Kubernetes cluster named `runefoble-local`.
3. Binds ports 80 and 443 to your host.
4. Installs the Traefik ingress controller into the cluster.

## Step 3: Validate and Deploy the Helm Chart
Lint and preview the rendered Kubernetes manifests:
```bash
make helm-lint
make helm-template
```
Deploy the entire Runefoble stack (Postgres, Silo, Zitadel, SpiceDB, OpenPanel, Mailpit, Loki/Grafana, Swagger UI, and microservices):
```bash
make helm-deploy
```

## Step 4: Verify Local Endpoints
Open your browser to:
- **Frontend App**: `http://localhost/`
- **Swagger UI API Hub**: `http://localhost/swagger-ui`
- **Identity Provider (Zitadel)**: `http://localhost/auth`
- **Mailpit Email Testing UI**: `http://localhost/mail/`
- **Observability (Grafana)**: `http://localhost:3001` (admin / admin)

## Step 5: Rapid Local Development (`make dev`)
For fast iterative feature work on the frontend and API Gateway without redeploying Helm charts, run:
```bash
make dev
```
This starts the Runefoble API Gateway on port 8000, checks gateway health, and concurrently launches the Vite dev server on `http://localhost:5173`. Vite automatically proxies API requests (`/api`, `/api/v1`, `/ws`, `/docs`, `/openapi.json`, `/mail`, `/oauth`) to local services without 502 Bad Gateway errors. Press `Ctrl+C` to cleanly stop all background processes.
