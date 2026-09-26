.PHONY: help setup cluster-up cluster-down helm-lint helm-template helm-deploy test lint build dev-frontend dev-storybook dev-api

CLUSTER_NAME ?= runefoble-local
KIND_CONFIG ?= deployments/kind/cluster-config.yaml
HELM_CHART ?= deployments/helm/runefoble
RELEASE_NAME ?= runefoble

help: ## Show this help message
	@echo "Runefoble Developer Interface"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install workspace Python dependencies and frontend packages
	@echo "==> Setting up UV workspace..."
	uv sync
	@echo "==> Setting up Frontend dependencies..."
	cd frontend && pnpm install

cluster-up: ## Create local Kind Kubernetes cluster with port mapping
	@echo "==> Creating Kind cluster $(CLUSTER_NAME)..."
	kind create cluster --name $(CLUSTER_NAME) --config $(KIND_CONFIG)
	@echo "==> Installing Traefik Ingress Controller..."
	kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v3.0/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml || true
	helm repo add traefik https://traefik.github.io/charts || true
	helm repo update || true
	helm upgrade --install traefik traefik/traefik --namespace kube-system --set ports.web.nodePort=30080 || true
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
	@echo "==> Deploying Runefoble Helm release..."
	helm upgrade --install $(RELEASE_NAME) $(HELM_CHART)

dev-frontend: ## Run frontend in hot-reloading dev mode
	@echo "==> Starting Vite development server..."
	cd frontend && pnpm run dev

dev-storybook: ## Run Storybook component studio
	@echo "==> Starting Storybook on port 6006..."
	cd frontend && pnpm run storybook

dev-api: ## Run API Gateway locally
	@echo "==> Starting Runefoble API Gateway..."
	uv run python gateway/api/src/gateway_api/main.py

test: ## Run test suite (pytest + frontend build verification)
	@echo "==> Running Python test suite..."
	uv run pytest
	@echo "==> Verifying frontend build..."
	cd frontend && pnpm run build

lint: ## Check types and code formatting
	@echo "==> Typechecking frontend..."
	cd frontend && pnpm exec tsc --noEmit
	@echo "==> Linting Helm charts..."
	helm lint $(HELM_CHART)

build: ## Build frontend assets and static Storybook
	@echo "==> Building frontend application..."
	cd frontend && pnpm run build
	@echo "==> Building static Storybook site..."
	cd frontend && pnpm exec storybook build --disable-telemetry --quiet
