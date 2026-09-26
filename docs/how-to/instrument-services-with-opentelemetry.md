# How-To: Instrument Services with OpenTelemetry

## Overview
Runefoble uses OpenTelemetry for distributed tracing and metric collection across microservices, API gateways, and asynchronous Redis Streams event processing. Traces allow monitoring latency budgets (such as the sub-500ms voice-to-board target) across distributed transactions.

## Prerequisites
Ensure OpenTelemetry packages are included in your service or library dependencies:
- `opentelemetry-api`
- `opentelemetry-sdk`
- `opentelemetry-exporter-otlp-proto-grpc`
- `opentelemetry-instrumentation-fastapi`

The OTel Collector runs locally via Helm at `http://otel-collector:4317` (gRPC) or `http://localhost:4317` in local development.

---

## Step 1: Initialize Telemetry in Service Lifecycle

In your service startup module (e.g. `main.py`):

```python
from fastapi import FastAPI
from runefoble_platform.config import PlatformSettings
from runefoble_platform.telemetry import init_telemetry

app = FastAPI(title="The Watcher Service")

# Standard middleware and routes registration
...

# Initialize OpenTelemetry and instrument the FastAPI app
init_telemetry("the-watcher", app=app)
```

`init_telemetry` automatically configures:
- A `TracerProvider` with `service.name` and deployment environment attributes.
- The `OTLPSpanExporter` pointing to the collector endpoint (`RUNEFOBLE_OTEL_EXPORTER_OTLP_ENDPOINT` or `http://otel-collector:4317`).
- Auto-instrumentation of incoming HTTP requests via `FastAPIInstrumentor`.

---

## Step 2: Instrument FastAPI Application Manually (Optional)

If you need fine-grained control over when the application is instrumented:

```python
from fastapi import FastAPI
from runefoble_platform.telemetry import init_telemetry, instrument_fastapi

app = FastAPI(title="The Watcher Service")
provider = init_telemetry("the-watcher")

# Instrument the FastAPI app instance explicitly
instrument_fastapi(app, tracer_provider=provider)
```

To clean up instrumentation during testing:

```python
from runefoble_platform.telemetry import uninstrument_fastapi, reset_tracer_provider

uninstrument_fastapi(app)
reset_tracer_provider()
```

---

## Step 3: Propagate Trace Context over Redis Streams

When emitting domain events to Redis Streams via `RedisStreamsEventBus.publish_event`, active W3C trace context (`traceparent`, `tracestate`) is automatically injected into both the Redis stream entry fields and domain event metadata:

```python
from runefoble_events.events import TokenMoved
from runefoble_platform.redis_bus import RedisStreamsEventBus

event_bus = RedisStreamsEventBus()

# When executed inside an active trace, traceparent is automatically attached:
event = TokenMoved(
    aggregate_id=session_id,
    token_id="token-42",
    name="Valeros",
    from_x=0,
    from_y=0,
    to_x=2,
    to_y=3,
)
await event_bus.publish_event("runefoble.events.board", event)
```

When consuming events in a consumer group worker, extract the carrier to maintain the span tree across the distributed boundary:

```python
from runefoble_platform.telemetry import extract_trace_context, get_tracer

tracer = get_tracer("runefoble.workers")


def process_traced_event(event_data: dict) -> None:
    extracted_ctx = extract_trace_context(event_data)

    with tracer.start_as_current_span("consume_domain_event", context=extracted_ctx):
        # Process domain state mutation within parent trace context
        ...
```

---

## Step 4: Verify in Grafana Dashboards

1. Open Grafana at `http://localhost:3001` (default admin credentials: `admin` / `admin`).
2. Navigate to **Explore** -> **OpenTelemetry / Loki**.
3. Search for trace ID or service name `the-watcher` or `gateway-api` to inspect waterfall spans and execution latencies.
