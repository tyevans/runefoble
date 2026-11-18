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
4. Installs the Traefik ingress controller into the cluster and waits until its rollout completes.

The command stops at the first failed step and exits with a non-zero status. It prints `Cluster is ready!` only when Traefik is running.
If the command fails, fix the error and run `make cluster-up` again. You can also check Traefik with `kubectl -n kube-system rollout status deploy/traefik`.

SpiceDB is not exposed on the host. To reach its gRPC port from the host, run `kubectl port-forward svc/spicedb 50051:50051`.

## Step 3: Build and Load the Service Images
Build every Python service image and load it into the Kind cluster:
```bash
make images
```
This command builds each service from `deployments/docker/python-service.Dockerfile`
and tags it `runefoble/<service>:0.1.0`. It then runs `kind load docker-image` for each tag.
Helm references these tags, so run this step before `make helm-deploy`.

## Step 4: Validate and Deploy the Helm Chart
Lint and preview the rendered Kubernetes manifests:
```bash
make helm-lint
make helm-template
```
Deploy the entire Runefoble stack (Postgres, Silo, Zitadel, SpiceDB, OpenPanel, Mailpit, Loki/Grafana, Swagger UI, and microservices):
```bash
make cluster-up images helm-deploy
```
Run the targets in this order. `make helm-deploy` does not build images by itself.

The chart creates the Secret `runefoble-credentials` from the `credentials` block in `values.yaml`. The values in that block are **dev-only**. They are public in this repository, so never deploy them to a shared cluster. See [Chart Credentials](../reference/platform-services.md#chart-credentials) for the keys and for the `credentials.existingSecret` setting that other environments need.

## Step 5: Verify Local Endpoints
Open your browser to:
- **Frontend App**: `http://localhost/`
- **Swagger UI API Hub**: `http://localhost/swagger-ui`
- **Identity Provider (Zitadel)**: `http://auth.localhost`. Chromium and Firefox resolve `*.localhost` to your machine. For `curl`, add `-H "Host: auth.localhost"` to the request, for example `curl -H "Host: auth.localhost" http://localhost/.well-known/openid-configuration`.
  - First run: the chart does not create the sign-in application (`runefoble-web`). Follow the two-step install in [Authenticate with Zitadel OIDC](../how-to/authenticate-with-zitadel-oidc.md#bootstrap-the-zitadel-project-and-application). It creates the project, the application, and the Secret `runefoble-zitadel-client` that the frontend reads.
- **Mailpit Email Testing UI**: `http://localhost/mail/`
- **Observability (Grafana)**: `http://localhost:3001` (admin / admin, dev-only value from `credentials.grafana.adminPassword`)

## Step 6: Rapid Local Development (`make dev`)
For fast iterative feature work on the frontend and API Gateway without redeploying Helm charts, export the SpiceDB preshared key and run:
```bash
export RUNEFOBLE_SPICEDB_PRESHARED_KEY=runefoble_secret_key   # DEV-ONLY: the value of credentials.spicedb.presharedKey in values.yaml
make dev
```
The key has no default. Services refuse to start without it.
This starts the Runefoble API Gateway on port 8000, checks gateway health, and concurrently launches the Vite dev server on `http://localhost:5173`. Vite automatically proxies API requests (`/api`, `/api/v1`, `/ws`, `/docs`, `/openapi.json`, `/mail`, `/oauth`) to local services without 502 Bad Gateway errors. Press `Ctrl+C` to cleanly stop all background processes.
