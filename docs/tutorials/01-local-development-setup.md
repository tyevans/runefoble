# Tutorial 01: Local Development Setup with Kind and Helm

## Objective
In this tutorial, you will create a local Kind (Kubernetes in Docker) cluster, build and load the service images, deploy the Runefoble stack with Helm, and check the endpoints. You will also run the rapid development loop with `make dev`.

Run the steps in order. Each step ends with an expected result. If a step does not match, stop and fix it before you go on.

## Prerequisites
- Docker running locally. `docker info` prints server details and no error.
- `uv` (>= 0.8.0). Python 3.13 or later. `uv sync` installs the Python version the workspace requires when it is missing.
- `node` (>= 20) and `pnpm`.
- `kubectl`. Check it with `kubectl version --client`.
- `helm` (>= 3.10).
- `make`.
- `curl`.

`make setup` installs `kind` into `~/.local/bin` when `kind` is not on your `PATH`.

## Step 1: Install Dependencies
Run the setup command. It installs the Python workspace and the frontend packages:
```bash
make setup
```
Expected result: `make setup` ends with no error. Then run this command:
```bash
uv run python -c 'print(1)'
```
It prints `1`.

## Step 2: Create the Kind Cluster and Traefik
Run:
```bash
make cluster-up
```
This command:
1. Reads `deployments/kind/cluster-config.yaml`.
2. Creates a local Kubernetes cluster named `runefoble-local`. It skips this when the cluster exists.
3. Binds host ports 80 and 443 to the cluster.
4. Installs the Traefik ingress controller in the `kube-system` namespace. It waits until the rollout completes.

The command stops at the first failed step and exits with a non-zero status. Fix the error and run `make cluster-up` again.

Data lives in volumes. PostgreSQL, Silo, and Redis each keep their data on a PersistentVolumeClaim. A pod restart keeps the data. `make cluster-down` deletes the cluster and every volume in it. Use it only when you want an empty stack. It deletes every event store, the Zitadel and SpiceDB data, the stored assets, and the Redis streams.

Check Traefik:
```bash
kubectl -n kube-system rollout status deploy/traefik
```
Expected result: `make cluster-up` prints `Cluster is ready! Ingress on localhost:80`. The `rollout status` command prints `deployment "traefik" successfully rolled out`.

SpiceDB does not have a host port. Step 6 describes how to reach it.

## Step 3: Build and Load the Service Images
Build every service image and load it into the Kind cluster:
```bash
make images
```
This command builds 15 images and tags each one as `runefoble/<service>:0.1.0`:
- 13 Python services from `deployments/docker/python-service.Dockerfile`.
- `runefoble/audience-studio` from `services/audience_studio/Dockerfile`.
- `runefoble/frontend` from `frontend/Dockerfile`.

After each build, the command runs `kind load docker-image` for that tag. Helm references these tags. Run this step before `make helm-deploy`.

Expected result: `make images` ends with the line `Loading runefoble/frontend:0.1.0 into Kind cluster runefoble-local` and no error. Then check the loaded images:
```bash
docker exec runefoble-local-control-plane crictl images | grep -c runefoble
```
It prints `15`.

## Step 4: Validate and Deploy the Helm Chart
Lint the chart and preview the rendered manifests:
```bash
make helm-lint
make helm-template
```
Expected result: `make helm-lint` prints `1 chart(s) linted, 0 chart(s) failed`. `make helm-template` prints the manifests and exits with status 0.

Deploy the stack. This deploys Postgres, Redis, Silo, Zitadel, SpiceDB, OpenPanel, Mailpit, Loki, Grafana, Swagger UI, and the microservices:
```bash
make cluster-up images helm-deploy
```
Run the targets in this order. `make helm-deploy` does not build images. It deploys the `runefoble` release to the `default` namespace. It does not wait for the pods, so check them:
```bash
kubectl get pods
```
Wait until each pod shows `Running`. The pods of the Jobs `spicedb-schema-migration` and `zitadel-bootstrap` show `Completed`. A clean install from an empty namespace finishes its Helm hooks in about one minute. `make helm-deploy` returns after that. Zitadel starts with its Postgres database and writes the admin token to a Secret without any manual step. Then check the gateway through the ingress:
```bash
curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost/healthz
```
Expected result: `200`. The body is a JSON report. Its `downstream_services` field shows the health of each service that the gateway probes.

The chart creates the Secret `runefoble-credentials` from the `credentials` block in `values.yaml`. The values in that block are **dev-only**. They are public in this repository, so never deploy them to a shared cluster. See [Chart Credentials](../reference/platform-services.md#chart-credentials) for the keys and for the `credentials.existingSecret` setting that other environments need.

## Step 5: Verify Local Endpoints
Check each endpoint:

| Endpoint | Check | Expected result |
|---|---|---|
| Frontend App | `curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost/` | `200` |
| Swagger UI API Hub | Open `http://localhost/swagger-ui` in a browser. | The page title is `Swagger UI`. |
| Identity Provider (Zitadel) | `curl -fsS -o /dev/null -w "%{http_code}\n" -H "Host: auth.localhost" http://localhost/.well-known/openid-configuration` | `200` |
| Mailpit Email Testing UI | `curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost/mail/` | `200` |

Zitadel uses the host name `auth.localhost`. Chromium and Firefox resolve `*.localhost` to your machine. For `curl`, send the `Host` header as shown.

**Sign-in application.** The bootstrap Job creates the Zitadel project and the sign-in application (`runefoble-web`) on each install. It writes the Secret `runefoble-zitadel-client` that the frontend reads. No manual step is needed. See [Authenticate with Zitadel OIDC](../how-to/authenticate-with-zitadel-oidc.md#bootstrap-the-zitadel-project-and-application).

**Grafana.** The chart does not add an ingress route for Grafana. Open a port-forward in its own terminal. It runs until you press `Ctrl+C`:
```bash
kubectl port-forward svc/grafana 3001:3001
```
Then open `http://localhost:3001/login`. Expected result: the Grafana login page loads (`200`). Sign in as `admin` with the password `admin`. This is the dev-only value of `credentials.grafana.adminPassword`.

## Step 6: Rapid Local Development (`make dev`)
Use `make dev` to work on the frontend and the API Gateway. It does not redeploy the Helm chart. The gateway runs on your host. The cluster supplies Redis and SpiceDB.

Export the required settings. Every value below is **DEV-ONLY**. It is public in this repository. Take each value from `values.yaml`:
```bash
export RUNEFOBLE_SPICEDB_PRESHARED_KEY=runefoble_secret_key       # credentials.spicedb.presharedKey
export RUNEFOBLE_SERVICE_CREDENTIAL=runefoble-dev-service-credential   # credentials.serviceCredential
```
Both values have no default. The gateway refuses to start without them. The gateway also refuses to start without Redis (ADR-0015).

Then run:
```bash
make dev
```
`make dev` does the following:
1. Checks SpiceDB on `127.0.0.1:50051`. When the port is closed and the cluster has `svc/spicedb`, it starts `kubectl port-forward svc/spicedb 50051:50051`. When the cluster is not reachable, it prints a warning and continues.
2. Checks Redis at `RUNEFOBLE_REDIS_URL` (default `redis://localhost:6379/0`). When the port is closed and the cluster has `svc/runefoble-redis`, it starts a port-forward to that Service. When neither answers, it exits with an error. Run `make cluster-up` first, or set `RUNEFOBLE_REDIS_URL` to a running Redis.
3. Starts the API Gateway on port 8000 and waits for its health check.
4. Starts the Vite dev server on port 5173.

Expected result: the log prints `API Gateway is healthy and ready!` and `Ready! App Shell available at http://localhost:5173`. Then check both ports in a second terminal:
```bash
curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost:8000/healthz
curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost:5173/healthz
```
Both print `200`. The second command checks the Vite proxy. Press `Ctrl+C` in the `make dev` terminal to stop all background processes. The port-forwards and the gateway stop with it, even when the orchestrator is killed with `SIGKILL` on Linux.

### Run the SpiceDB port-forward by hand
`make dev` starts the SpiceDB port-forward only when port 50051 is closed. Other targets do not start it. For example, `make dev-api` does not. Run the port-forward yourself before you run such a target:
```bash
kubectl port-forward svc/spicedb 50051:50051
```

### Vite proxy paths
The Vite dev server (`frontend/vite.config.ts`) forwards these paths:

| Path | Target | Default target URL |
|---|---|---|
| `/api`, `/api/v1` | API Gateway | `http://localhost:8000` (`GATEWAY_API_URL`) |
| `/ws` | API Gateway (WebSocket) | `ws://localhost:8000` (`GATEWAY_WS_URL`) |
| `/docs`, `/redoc`, `/openapi.json` | API Gateway | `http://localhost:8000` (`GATEWAY_API_URL`) |
| `/campaigns`, `/healthz` | API Gateway | `http://localhost:8000` (`GATEWAY_API_URL`) |
| `/mail`, `/mailpit` | Mailpit | `http://localhost:8025` (`MAILPIT_URL`) |
| `/oauth` | Zitadel | `http://localhost:8080` (`ZITADEL_URL`) |

The Kind cluster does not expose Mailpit or Zitadel on the host. When you use `/mail`, `/mailpit`, or `/oauth` in `make dev`, port-forward the service to the default port (`kubectl port-forward svc/mailpit 8025:8025` or `kubectl port-forward svc/zitadel 8080:8080`). Or set `MAILPIT_URL` or `ZITADEL_URL` to another address.

### Event store
Services use PostgreSQL by default (`RUNEFOBLE_EVENT_STORE_BACKEND=postgresql`). The default `make dev` run starts the gateway and the Vite server. It does not start the aggregate-owning services.

To run an aggregate-owning service outside the cluster without PostgreSQL, set `RUNEFOBLE_EVENT_STORE_BACKEND=memory` for that process. The service then keeps events only in its own memory. Staging and production refuse `memory`.
