.PHONY: help setup install-tools cluster-up cluster-down images voice-model-cache helm-lint helm-template helm-check-event-store helm-deploy test test-entrypoints test-property test-mutation test-e2e test-e2e-ui test-bdd lint lint-fix build dev dev-frontend dev-storybook dev-api dev-worker deploy-remote-worker pre-commit health-check clean-worktrees backlog-worker docs-build docs-serve prd-audit prd-decompose prd-create prd-sync


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

clean-worktrees: ## Clean up merged and stale git worktrees safely
	@./scripts/cleanup-worktrees.sh $(ARGS)

prd-audit: ## Audit PRDs, buffer health, and granularity
	@python3 -m tools.prd_pipeline.cli audit

prd-decompose: ## Decompose PRDs into ADR spikes and vertical slices (ARGS="--prd PRD-0014")
	@python3 -m tools.prd_pipeline.cli decompose $(ARGS)

prd-create: ## Scaffold a new PRD document (ARGS="--title '...'")
	@python3 -m tools.prd_pipeline.cli create $(ARGS)

prd-sync: ## Synchronize PRD, User Story, and Backlog registries
	@python3 -m tools.prd_pipeline.cli sync

backlog-worker: ## Run autonomous backlog execution engine (ARGS="--drain --concurrency 2")
	@python3 -m tools.backlog_engine.cli $(ARGS)

visualize-project: ## Launch dynamic docs/project content visualizer web application
	@python3 -m tools.project_visualizer.cli serve

visualize-project-build: ## Build standalone HTML bundle for docs/project visualizer
	@python3 -m tools.project_visualizer.cli build --out dist/project-visualizer.html

docs-build: ## Build static documentation site with Zensical and integrated project visualizer
	@python3 scripts/build_docs.py

docs-serve: ## Serve documentation site locally with live preview
	@python3 scripts/build_docs.py
	@uv run zensical serve

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
	kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v3.0/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml
	@helm repo list 2>/dev/null | grep -q "^traefik[[:space:]]" || helm repo add traefik https://traefik.github.io/charts
	helm repo update
	helm upgrade --install traefik traefik/traefik --namespace kube-system --set ports.web.nodePort=30080 --set ports.web.hostPort=80 --set ports.websecure.hostPort=443
	kubectl -n kube-system rollout status deploy/traefik --timeout=300s
	@echo "==> Cluster is ready! Ingress on localhost:80"

cluster-down: ## Delete local Kind Kubernetes cluster
	@echo "==> Tearing down Kind cluster $(CLUSTER_NAME)..."
	kind delete cluster --name $(CLUSTER_NAME)

# Python service images built by `make images`.
# Row format: image-name|uv-package|ASGI-app|port|system-packages (no spaces inside a row).
# Each port must equal services.*.port in deployments/helm/runefoble/values.yaml.
# The system-packages field is empty unless the service needs Debian packages at runtime.
IMAGE_VERSION ?= 0.1.0
PYTHON_DOCKERFILE ?= deployments/docker/python-service.Dockerfile
PYTHON_IMAGE_ROWS = \
	'gateway-api|gateway-api|gateway_api.main:app|8000|' \
	'the-watcher|the-watcher|the_watcher.main:app|8001|' \
	'board-state|board-state|board_state.main:app|8002|' \
	'character-sheet|character-sheet|character_sheet.main:app|8003|' \
	'game-session|game-session|game_session.main:app|8004|' \
	'voice-agent|voice-agent|voice_agent.main:app|8005|espeak-ng' \
	'campaign-lore|campaign-lore|campaign_lore.main:app|8006|' \
	'rules-compendium|rules-compendium|rules_compendium.main:app|8007|' \
	'asset-forge|asset-forge|asset_forge.main:app|8008|' \
	'soundscape|soundscape|soundscape.main:app|8009|' \
	'campaign-analytics|campaign-analytics|campaign_analytics.main:app|8011|' \
	'inference-worker|inference-worker|inference_worker.api:app|8100|'

# Speech model pre-fetch for voice-agent (TASK-0676). The model downloads on the host,
# then the files are copied into the running voice-agent pod's model cache volume.
VOICE_MODEL_SIZE ?= tiny.en
VOICE_MODEL_HOST_DIR ?= .cache/voice-models
VOICE_MODEL_POD_DIR ?= /var/lib/runefoble/whisper

images: ## Build every service image (Python and Node) and load it into the Kind cluster
	@for row in $(PYTHON_IMAGE_ROWS); do \
	  name=$$(echo "$$row" | cut -d'|' -f1); \
	  svc=$$(echo "$$row" | cut -d'|' -f2); \
	  app=$$(echo "$$row" | cut -d'|' -f3); \
	  port=$$(echo "$$row" | cut -d'|' -f4); \
	  pkgs=$$(echo "$$row" | cut -d'|' -f5); \
	  echo "==> Building runefoble/$$name:$(IMAGE_VERSION) (package $$svc, port $$port)"; \
	  docker build -f $(PYTHON_DOCKERFILE) --build-arg SERVICE=$$svc --build-arg APP=$$app --build-arg PORT=$$port --build-arg SYSTEM_PACKAGES="$$pkgs" -t runefoble/$$name:$(IMAGE_VERSION) . || exit 1; \
	  echo "==> Loading runefoble/$$name:$(IMAGE_VERSION) into Kind cluster $(CLUSTER_NAME)"; \
	  kind load docker-image runefoble/$$name:$(IMAGE_VERSION) --name $(CLUSTER_NAME) || exit 1; \
	done
	@echo "==> Building runefoble/audience-studio:$(IMAGE_VERSION) (Node service, port 8010)"
	docker build -f services/audience_studio/Dockerfile -t runefoble/audience-studio:$(IMAGE_VERSION) . || exit 1
	@echo "==> Loading runefoble/audience-studio:$(IMAGE_VERSION) into Kind cluster $(CLUSTER_NAME)"
	kind load docker-image runefoble/audience-studio:$(IMAGE_VERSION) --name $(CLUSTER_NAME)

voice-model-cache: ## Pre-fetch the faster-whisper model and copy it into the voice-agent pod (Kind)
	@echo "==> Downloading faster-whisper $(VOICE_MODEL_SIZE) into $(VOICE_MODEL_HOST_DIR)..."
	uv run python -c "from faster_whisper import WhisperModel; WhisperModel('$(VOICE_MODEL_SIZE)', device='cpu', compute_type='int8', download_root='$(VOICE_MODEL_HOST_DIR)')"
	@pod=$$(kubectl get pod -l app=voice-agent -o jsonpath='{.items[0].metadata.name}') || exit 1; \
	  echo "==> Copying model cache into pod $$pod:$(VOICE_MODEL_POD_DIR)"; \
	  kubectl cp $(VOICE_MODEL_HOST_DIR)/. $$pod:$(VOICE_MODEL_POD_DIR) || exit 1

helm-lint: ## Validate Helm chart syntax
	@echo "==> Linting Helm chart..."
	helm lint $(HELM_CHART)

helm-template: ## Render and inspect Helm manifests
	@echo "==> Rendering Helm templates..."
	helm template $(RELEASE_NAME) $(HELM_CHART)

helm-check-event-store: ## Fail if an aggregate-owning service lacks the PostgreSQL event store
	@python3 scripts/check_helm_event_store.py $(HELM_CHART)

helm-deploy: ## Deploy Runefoble stack to current Kubernetes context
	@echo "==> Ensuring active kubectl context is kind-$(CLUSTER_NAME)..."
	@kubectl config use-context kind-$(CLUSTER_NAME) 2>/dev/null || true
	@kubectl cluster-info >/dev/null 2>&1 || (echo "Error: Kubernetes cluster is unreachable. Run 'make cluster-up' first." && exit 1)
	@echo "==> Deploying Runefoble Helm release..."
	helm upgrade --install $(RELEASE_NAME) $(HELM_CHART)

dev: ## Run API Gateway and Vite frontend concurrently with health check gating
	@python3 scripts/dev_server.py $(ARGS)

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

test-bdd: ## Typecheck e2e steps, reject unused steps, validate Gherkin syntax
	@echo "==> Typechecking e2e suite..."
	@pnpm run e2e:typecheck
	@echo "==> Checking for unused e2e step definitions..."
	@uv run python scripts/check_e2e_unused_steps.py
	@echo "==> Validating Gherkin feature syntax and step definitions..."
	@pnpm exec bddgen

test-e2e: ## Run headless Playwright BDD suite across standard browsers
	@echo "==> Running Playwright BDD end-to-end tests..."
	@pnpm exec bddgen
	@pnpm exec playwright test $(ARGS)

test-e2e-ui: ## Launch interactive Playwright UI mode for live debugging
	@echo "==> Launching Playwright interactive UI..."
	@pnpm exec bddgen
	@pnpm exec playwright test --ui $(ARGS)

lint: ## Check types, Ruff lint, format, and Helm
	@echo "==> Checking Ruff lint rules..."
	uv run ruff check .
	@echo "==> Checking Ruff formatting..."
	uv run ruff format --check .
	@echo "==> Typechecking inference worker..."
	uv run mypy services/inference_worker/src
	@echo "==> Typechecking frontend..."
	cd frontend && pnpm exec tsc --noEmit
	@echo "==> Typechecking e2e suite..."
	pnpm run e2e:typecheck
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
