---
id: 0029
title: OpenTelemetry Distributed Tracing, Metrics & Collector Helm Integration
status: Proposed
created: 2026-09-25
dependencies: [TASK-0001, TASK-0008]
governing_adrs: [ADR-0005, ADR-0006, ADR-0007]
target_release: 0.1.0
---

# TASK-0029 — OpenTelemetry Distributed Tracing, Metrics & Collector Helm Integration

## Summary
Integrate OpenTelemetry instrumentation across all FastAPI services and Redis Streams event bus subscribers in `libs/runefoble_platform`. Propagate W3C Trace Context across HTTP headers and CloudEvents metadata so distributed transactions (e.g. Speech -> Intent -> Board Move -> Event -> Audio Synth) can be visualized end-to-end in Grafana. Deploy the OpenTelemetry Collector container in the Helm chart to aggregate and route traces to Loki and Grafana.

## INVEST Criteria Evaluation
- **Independent (I)**: Decoupled from specific game domain features. Can be enabled across platform libraries without breaking existing endpoint contracts.
- **Negotiable (N)**: Collector configuration, sampling rates (e.g. 100% in dev, probabilistic in prod), and exporter protocol (OTLP gRPC/HTTP) can be tuned without rewriting application code.
- **Valuable (V)**: Delivers instant operational observability for the sub-500ms voice-to-board budget, pinpointing latency bottlenecks between Whisper STT, The Watcher, and Board State.
- **Estimable (E)**: Standard OpenTelemetry Python instrumentation patterns (`opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-redis`); governed by ADR-0005.
- **Small (S)**: Scope is confined to platform library setup (`telemetry.py`), Helm collector manifest additions, and gateway/service middleware hooks, keeping each file under 500 lines.
- **Testable (T)**: Verifiable via blackbox test using `InMemorySpanExporter` verifying that invoking public HTTP routes produces valid spans with expected service attributes and trace propagation headers.

## Governing Architecture & ADRs
- **ADR-0005**: Kubernetes-First Infrastructure with Helm and Kind (`observability.yaml`).
- **ADR-0006**: Redis Streams Event Streaming (trace context injection in CloudEvents metadata).
- **ADR-0007**: Domain-Driven Design Architecture (cross-cutting observability concerns centralized in `libs/runefoble_platform`).

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Telemetry Platform Module (`libs/runefoble_platform/src/runefoble_platform/telemetry.py`)**:
   - `init_telemetry(service_name: str, settings: PlatformSettings)` configuring tracer provider, OTLP gRPC exporter, and FastAPI auto-instrumentor.
   - W3C trace context injector/extractor helper for Redis Streams event payloads.
2. **Package Dependencies**:
   - Add `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`, and `opentelemetry-instrumentation-fastapi` to `libs/runefoble_platform/pyproject.toml`.
3. **Helm Chart Integration (`deployments/helm/runefoble/templates/observability.yaml`)**:
   - Add OpenTelemetry Collector Deployment and Service definitions (ports 4317 gRPC, 4318 HTTP).
   - Configure Grafana datasource provisioning ConfigMap pointing to Loki and Prometheus/OTel collector.
4. **Blackbox TDD Suite (`tests/test_blackbox_opentelemetry.py`)**:
   - Blackbox test exercising gateway frontdoor HTTP route and verifying spans are emitted to an in-memory exporter with correct attributes (`service.name`, `http.route`, `http.status_code`).
5. **Diataxis Documentation**:
   - Create `docs/how-to/instrument-services-with-opentelemetry.md`.
6. **File Invariant Check**:
   - All touched files remain strictly under 500 lines.
