# Runefoble

> An imaginative gaming platform for storytellers of all ages (a collaborative tabletop roleplaying service).

Using advanced AI (LLMs and machine learning models), Runefoble delivers the highest quality, lowest friction collaborative storytelling experience in the world.
Speak and the board obeys: natural speech is parsed into game actions and applied directly to the game state, while The Watcher and the Game Master explore the narrative consequences.

## Key Features
- **The Watcher AI Engine**: Speech-to-intent parsing, real-time board animations, autonomous DMing, and missing player AI stand-ins.
- **Absence Penalties ("Session Miss Costs")**: Missing players are piloted by AI with DM-inflicted penalties (e.g. "Drunk", "Foolishness").
- **Fine-Grained Authorization**: SpiceDB Zanzibar object-level permissions (`runefoble.zed`).
- **Unified Swagger Hub**: Swagger UI aggregating OpenAPI specs from all microservices.
- **Component-Driven Frontend**: Built with Lit (Web Components), Vite, and Storybook.
- **Kubernetes-First from Day 1**: Kind for local development, Traefik ingress, and umbrella Helm chart (`deployments/helm/runefoble`).

## Quick Start

```bash
# 1. Setup Python UV workspace and frontend dependencies
make setup

# 2. Run Python tests and verify frontend build
make test

# 3. Launch local Kind Kubernetes cluster with Traefik ingress
make cluster-up

# 4. Deploy full platform via Helm
make helm-deploy

# 5. Run Storybook component studio
make dev-storybook
```

## Documentation
- **Operating Manual for AI Agents**: [`AGENTS.md`](AGENTS.md)
- **Diataxis Documentation**:
  - [Tutorials](docs/tutorials/)
  - [How-To Guides](docs/how-to/)
  - [Reference](docs/reference/)
  - [Explanation](docs/explanation/)
- **Project Management**:
  - [ADR Registry](docs/project/adrs/REGISTRY.md)
  - [Product Requirements](docs/project/product/REGISTRY.md)
  - [User Stories](docs/project/user_stories/REGISTRY.md)
  - [Backlog](docs/project/backlog/PRIORITY.md)
