#!/usr/bin/env bash
# Runs the commands of docs/tutorials/01-local-development-setup.md in order and checks each
# observable result. Run it by hand on a machine with Docker, kind, kubectl, helm, uv, and pnpm.
# It is not part of CI. It creates the Kind cluster and deploys the stack.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GRAFANA_PF_PID=""
cleanup() {
  if [[ -n "$GRAFANA_PF_PID" ]]; then
    kill "$GRAFANA_PF_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# expect_status <expected> <url> [extra curl args...]
expect_status() {
  local expected="$1" url="$2"
  shift 2
  local actual
  actual="$(curl -s -o /dev/null -w '%{http_code}' "$@" "$url" || true)"
  if [[ "$actual" != "$expected" ]]; then
    echo "FAIL: $url returned $actual, expected $expected" >&2
    exit 1
  fi
  echo "OK: $url returned $expected"
}

echo "==> Step 1: make setup"
make setup
uv run python -c 'print(1)' | grep -qx '1'

echo "==> Step 2: make cluster-up and Traefik"
make cluster-up
kubectl -n kube-system rollout status deploy/traefik --timeout=300s

echo "==> Step 3: make images"
make images
count="$(docker exec runefoble-local-control-plane crictl images | grep -c runefoble)"
if [[ "$count" != "15" ]]; then
  echo "FAIL: $count runefoble images on the Kind node, expected 15" >&2
  exit 1
fi
echo "OK: 15 runefoble images are loaded"

echo "==> Step 4: helm-lint, helm-template, helm-deploy"
make helm-lint
make helm-template >/dev/null
make helm-deploy

echo "==> Step 4: wait for the gateway through the ingress (up to 15 minutes)"
deadline=$((SECONDS + 900))
until curl -fsS -o /dev/null http://localhost/healthz 2>/dev/null; do
  if (( SECONDS >= deadline )); then
    echo "FAIL: gateway health did not return 200 within 15 minutes" >&2
    kubectl get pods >&2 || true
    exit 1
  fi
  sleep 5
done
expect_status 200 http://localhost/healthz

echo "==> Step 5: endpoints"
expect_status 200 http://localhost/
expect_status 200 http://localhost/mail/
expect_status 200 http://localhost/.well-known/openid-configuration -H "Host: auth.localhost"

echo "==> Step 5: Grafana through port-forward"
kubectl port-forward svc/grafana 3001:3001 >/dev/null 2>&1 &
GRAFANA_PF_PID=$!
grafana_deadline=$((SECONDS + 60))
until curl -fsS -o /dev/null http://localhost:3001/login 2>/dev/null; do
  if (( SECONDS >= grafana_deadline )); then
    echo "FAIL: Grafana did not answer on http://localhost:3001/login" >&2
    exit 1
  fi
  sleep 2
done
expect_status 200 http://localhost:3001/login

echo "Tutorial 01 cluster steps passed. Run make dev (Step 6) by hand. It needs the Redis service."
