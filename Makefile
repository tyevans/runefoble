.PHONY: help setup install-tools cluster-up cluster-down helm-lint helm-template helm-deploy test test-entrypoints test-property test-mutation lint lint-fix build dev-frontend dev-storybook dev-api dev-worker deploy-remote-worker pre-commit health-check backlog-worker

CLUSTER_NAME ?= runefoble-local
KIND_CONFIG ?= deployments/kind/cluster-config.yaml
HELM_CHART ?= deployments/helm/runefoble
RELEASE_NAME ?= runefoble

help: ## Show this help message
	@echo "Runefoble Developer Interface"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

health-check: ## Inspect codebase file length invariants and backlog ready buffer
	@python3 scripts/health_check.py

backlog-worker: ## Run autonomous backlog execution engine (ARGS="--drain --concurrency 2")
	@python3 -m tools.backlog_engine.cli $(ARGS)

setup: install-tools ## Install workspace Python dependencies and frontend packages
	@echo "==> Setting up UV workspace..."
	uv sync
	@echo "==> Setting up Frontend dependencies..."
	cd frontend && pnpm install

install-tools: ## Check or auto-install local kind binary into ~/.local/bin
	@which kind >/dev/null 2>&1 || (echo "==> Installing kind to ~/.local/bin/kind..." && mkdir -p ~/.local/bin && curl -Lo ~/.local/bin/kind https://kind.sigs.k8s.io/dl/v0.27.0/kind-linux-amd64 && chmod +x ~/.local/bin/kind)
	@which uv >/dev/null 2>&1 || echo "Warning: uv not found in PATH"
	@which pnpm >/dev/null 2>&1 || echo "Warning: pnpm not found in PATH"
	@which helm >/dev/null 2>&1 || echo "Warning: helm not found in PATH"
	@which docker >/dev/null 2>&1 || echo "Warning: docker not found in PATH"

cluster-up: install-tools ## Create local Kind Kubernetes cluster with port mapping
	@echo "==> Checking if Kind cluster '$(CLUSTER_NAME)' exists..."
	@kind get clusters 2>/dev/null | grep -q "^$(CLUSTER_NAME)$$" || (echo "==> Creating Kind cluster $(CLUSTER_NAME)..." && kind create cluster --name $(CLUSTER_NAME) --config $(KIND_CONFIG))
	@echo "==> Setting active kubectl context to kind-$(CLUSTER_NAME)..."
	kubectl config use-context kind-$(CLUSTER_NAME)
	@echo "==> Installing Traefik Ingress Controller..."
	kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v3.0/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml 2>/dev/null || true
	helm repo add traefik https://traefik.github.io/charts 2>/dev/null || true
	helm repo update 2>/dev/null || true
	helm upgrade --install traefik traefik/traefik --namespace kube-system --set ports.web.nodePort=30080 --set ports.web.hostPort=80 --set ports.websecure.hostPort=443 2>/dev/null || true
	@echo "==> Cluster is ready! Ingress on localhost:80"

cluster-down: ## Delete local Kind Kubernetes cluster
	@echo "==> Tearing down Kind cluster $(CLUSTER_NAME)..."
	kind delete cluster --name $(CLUSTER_NAME)

helm-lint: ## Validate Helm chart syntax
	@echo "==> Linting Helm chart..."
	helm lint $(HELM_CHART)

helm-template: ## Render and inspect Helm manifests
	@echo "==> Rendering Helm templates..."
	helm template $(RELEASE_NAME) $(HELM_CHART)

helm-deploy: ## Deploy Runefoble stack to current Kubernetes context
	@echo "==> Ensuring active kubectl context is kind-$(CLUSTER_NAME)..."
	@kubectl config use-context kind-$(CLUSTER_NAME) 2>/dev/null || true
	@kubectl cluster-info >/dev/null 2>&1 || (echo "Error: Kubernetes cluster is unreachable. Run 'make cluster-up' first." && exit 1)
	@echo "==> Deploying Runefoble Helm release..."
	helm upgrade --install $(RELEASE_NAME) $(HELM_CHART)

dev-frontend: ## Run frontend in hot-reloading dev mode
	@echo "==> Starting Vite development server..."
	cd frontend && CHOKIDAR_USEPOLLING=true pnpm run dev

dev-storybook: ## Run Storybook component studio with watcher protection
	@echo "==> Starting Storybook on port 6006..."
	cd frontend && WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true pnpm run storybook

dev-api: ## Run API Gateway locally
	@echo "==> Starting Runefoble API Gateway..."
	uv run python gateway/api/src/gateway_api/main.py

dev-worker: ## Run AI inference worker locally
	@echo "==> Starting Runefoble AI Inference Worker..."
	uv run runefoble-inference-worker

deploy-remote-worker: ## Sync and set up inference worker on remote GPU host
	@echo "==> Syncing workspace to remote GPU host (debian@192.168.1.14)..."
	ssh debian@192.168.1.14 "mkdir -p ~/runefoble"
	rsync -avz --exclude '.git' --exclude '.venv' --exclude 'node_modules' --exclude '__pycache__' . debian@192.168.1.14:~/runefoble/
	ssh debian@192.168.1.14 "cd ~/runefoble && ~/.local/bin/uv sync"
	@echo "==> Remote worker synced. To run: ssh debian@192.168.1.14 'cd ~/runefoble && ~/.local/bin/uv run runefoble-inference-worker'"

test: ## Run complete test suite (unit, entrypoints, properties, frontend build)
	@echo "==> Running Python test suite..."
	uv run pytest
	@echo "==> Verifying frontend build..."
	cd frontend && pnpm run build

test-entrypoints: ## Test developer entrypoints, CLI tools, and microservice startups
	@echo "==> Running entrypoint tests..."
	uv run pytest tests/test_entrypoints.py

test-property: ## Run generative invariant property tests with Hypothesis
	@echo "==> Running Hypothesis property tests..."
	uv run pytest tests/test_properties.py

test-mutation: ## Run mutation testing with mutmut on core domain modules
	@echo "==> Running mutation tests..."
	uv run mutmut run || true
	uv run mutmut results || true

lint: ## Check types, Ruff lint, format, and Helm
	@echo "==> Checking Ruff lint rules..."
	uv run ruff check .
	@echo "==> Checking Ruff formatting..."
	uv run ruff format --check .
	@echo "==> Typechecking frontend..."
	cd frontend && pnpm exec tsc --noEmit
	@echo "==> Linting Helm charts..."
	helm lint $(HELM_CHART)

lint-fix: ## Automatically fix Ruff lint errors and format files
	@echo "==> Fixing lint and formatting with Ruff..."
	uv run ruff check --fix .
	uv run ruff format .

pre-commit: ## Run all pre-commit hooks across the repository
	@echo "==> Running pre-commit hooks..."
	uv run pre-commit run --all-files

build: ## Build frontend assets and static Storybook
	@echo "==> Building frontend application..."
	cd frontend && pnpm run build
	@echo "==> Building static Storybook site..."
	cd frontend && pnpm exec storybook build --disable-telemetry --quiet
