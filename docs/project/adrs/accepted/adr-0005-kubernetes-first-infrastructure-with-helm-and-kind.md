# ADR-0005: Kubernetes-First Infrastructure with Helm and Kind

## Context

Runefoble depends on multiple integrated systems:
- Traefik (Ingress / API load balancing)
- PostgreSQL (Primary state store)
- Silo (MinIO-fork S3 object storage for audio recordings & character art)
- Zitadel (Identity & OIDC container)
- SpiceDB (Zanzibar graph authorization engine)
- OpenPanel (Privacy-preserving analytics)
- OpenTelemetry Collector, Grafana, and Loki (Tracing & log aggregation)
- Microservices & Frontend

Running these services via ad-hoc docker scripts leads to environment disparity between local development and cloud production.

## Decision

We adopt a **Kubernetes-First infrastructure model from Day 1**:

1. **Kind (Kubernetes IN Docker)**: Local development uses a Kind cluster with port mapping (80/443 for Traefik).
2. **Umbrella Helm Chart**: All services, databases, and third-party containers are packaged into `deployments/helm/runefoble`.
3. **Swagger UI Aggregation**: The Helm chart deploys an official Swagger UI container configured to aggregate OpenAPI definitions from all backend services into a single unified dropdown interface.
4. **Makefile Interface**: Standardized targets (`make cluster-up`, `make helm-deploy`, `make test`) hide Kubernetes complexity from everyday development workflows.

## Consequences

- Local testing reflects identical container networking, ingress routing, and service discovery as production.
- Onboarding requires only Docker, Kind, Helm, and Make.
- CI/CD deploys the exact same Helm charts to cloud clusters.
