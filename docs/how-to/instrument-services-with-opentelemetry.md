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
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from runefoble_platform.config import PlatformSettings

def configure_telemetry(service_name: str, settings: PlatformSettings | None = None) -> None:
    settings = settings or PlatformSettings()
    
    resource = Resource.create({
        "service.name": service_name,
        "deployment.environment": settings.environment,
    })
    
    provider = TracerProvider(resource=resource)
    
    # Export spans to OTel Collector via OTLP gRPC
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
```

---

## Step 2: Instrument FastAPI Application

Auto-instrument incoming HTTP requests to produce spans with status codes and route templates:

```python
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app = FastAPI(title="The Watcher Service")
configure_telemetry("the-watcher")

# Instrument the FastAPI app instance
FastAPIInstrumentor.instrument_app(app)
```

---

## Step 3: Propagate Trace Context over Redis Streams

When emitting domain events to Redis Streams, inject the active W3C trace context into the event metadata:

```python
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

tracer = trace.get_tracer("runefoble.events")
propagator = TraceContextTextMapPropagator()

def publish_traced_event(event_bus, topic: str, event_data: dict) -> None:
    carrier: dict[str, str] = {}
    propagator.inject(carrier)
    
    # Attach carrier to CloudEvent extension headers
    event_data["traceparent"] = carrier.get("traceparent")
    event_bus.publish(topic, event_data)
```

When consuming events in a consumer group worker, extract the carrier to maintain the span tree:

```python
def process_traced_event(event_data: dict) -> None:
    carrier = {"traceparent": event_data.get("traceparent", "")}
    extracted_ctx = propagator.extract(carrier)
    
    with tracer.start_as_current_span("consume_domain_event", context=extracted_ctx):
        # Process domain state mutation within parent trace context
        ...
```

---

## Step 4: Verify in Grafana Dashboards

1. Open Grafana at `http://localhost:3001` (default admin credentials: `admin` / `admin`).
2. Navigate to **Explore** -> **Loki / Jaeger / OTLP**.
3. Search for trace ID or service name `the-watcher` or `gateway-api` to inspect waterfall spans and execution latencies.
