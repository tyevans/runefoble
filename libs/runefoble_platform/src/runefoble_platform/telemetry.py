"""Runefoble OpenTelemetry Instrumentation and Distributed Tracing Module.

Provides standard OpenTelemetry tracing initialization, FastAPI auto-instrumentation,
and W3C Trace Context propagation across HTTP boundaries and Redis Streams domain events.
"""

from __future__ import annotations

import contextlib
import json
import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from opentelemetry import context, trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from runefoble_platform.config import PlatformSettings

logger = logging.getLogger("runefoble.telemetry")

_propagator = TraceContextTextMapPropagator()


def reset_tracer_provider() -> None:
    """Reset the global TracerProvider singleton (primarily used in tests)."""
    trace._TRACER_PROVIDER = None
    if hasattr(trace, "_TRACER_PROVIDER_SET_ONCE"):
        trace._TRACER_PROVIDER_SET_ONCE._done = False


def init_telemetry(
    service_name: str,
    settings: PlatformSettings | None = None,
    app: Any | None = None,
    span_exporter: SpanExporter | None = None,
    use_otlp_exporter: bool | None = None,
    force: bool = False,
) -> TracerProvider:
    """Initialize OpenTelemetry tracer provider, exporter, and optional FastAPI instrumentation.

    Args:
        service_name: Unique identifier for the service (e.g. 'gateway-api', 'the-watcher').
        settings: Platform configuration settings. Defaults to PlatformSettings().
        app: Optional FastAPI application instance to auto-instrument.
        span_exporter: Custom SpanExporter (such as InMemorySpanExporter for testing).
        use_otlp_exporter: Override whether to configure OTLP gRPC export. Defaults to settings.otel_enabled.
        force: If True, resets any existing global tracer provider before configuration.

    Returns:
        The configured TracerProvider instance.
    """
    settings = settings or PlatformSettings()

    if force:
        reset_tracer_provider()

    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": settings.environment,
        }
    )

    provider = TracerProvider(resource=resource)

    if span_exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    else:
        should_export = (
            use_otlp_exporter if use_otlp_exporter is not None else settings.otel_enabled
        )
        if should_export:
            try:
                exporter = OTLPSpanExporter(
                    endpoint=settings.otel_exporter_otlp_endpoint,
                    insecure=True,
                )
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info(
                    "Configured OTLP gRPC trace exporter to %s for %s",
                    settings.otel_exporter_otlp_endpoint,
                    service_name,
                )
            except Exception as e:
                logger.warning(
                    "Failed to configure OTLP trace exporter for %s: %s",
                    service_name,
                    e,
                )

    # Register as global provider if none exists or if forced
    if trace._TRACER_PROVIDER is None or force:
        trace.set_tracer_provider(provider)

    if app is not None:
        instrument_fastapi(app, tracer_provider=provider)

    return provider


def instrument_fastapi(app: Any, tracer_provider: TracerProvider | None = None) -> None:
    """Auto-instrument a FastAPI application with OpenTelemetry middleware."""
    try:
        if getattr(app, "_is_instrumented_by_opentelemetry", False):
            FastAPIInstrumentor.uninstrument_app(app)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
        if getattr(app, "middleware_stack", None) is not None:
            app.middleware_stack = app.build_middleware_stack()
    except Exception as e:
        logger.debug("FastAPI instrumentation notice: %s", e)


def uninstrument_fastapi(app: Any) -> None:
    """Uninstrument a FastAPI application (useful for test isolation)."""
    with contextlib.suppress(Exception):
        FastAPIInstrumentor.uninstrument_app(app)
        if getattr(app, "middleware_stack", None) is not None:
            app.middleware_stack = app.build_middleware_stack()


def get_tracer(name: str = "runefoble") -> trace.Tracer:
    """Obtain a named OpenTelemetry tracer."""
    return trace.get_tracer(name)


def inject_trace_context(
    carrier: dict[str, Any] | Any | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Inject W3C trace context (traceparent, tracestate) into a dictionary or event object.

    Args:
        carrier: Target dictionary, DomainEvent, or None to create a new dictionary.
        ctx: Explicit OpenTelemetry Context to inject. Defaults to current active context.

    Returns:
        The carrier dictionary containing injected trace headers.
    """
    if carrier is None:
        carrier_dict: dict[str, Any] = {}
        _propagator.inject(carrier_dict, context=ctx)
        return carrier_dict

    if isinstance(carrier, dict):
        _propagator.inject(carrier, context=ctx)
        if "metadata" in carrier and isinstance(carrier["metadata"], dict):
            _propagator.inject(carrier["metadata"], context=ctx)
        return carrier

    # Handle domain event objects with metadata attribute
    if hasattr(carrier, "metadata"):
        if carrier.metadata is None:
            carrier.metadata = {}
        if isinstance(carrier.metadata, dict):
            _propagator.inject(carrier.metadata, context=ctx)

    temp_carrier: dict[str, str] = {}
    _propagator.inject(temp_carrier, context=ctx)
    return temp_carrier


def extract_trace_context(carrier: dict[str, Any] | Any | None = None) -> Context:
    """Extract W3C trace context from event dictionaries, Redis stream fields, or domain event metadata.

    Args:
        carrier: Redis stream entry dict, event dictionary, or domain event instance.

    Returns:
        Extracted OpenTelemetry Context (or empty context if not present / invalid).
    """
    if carrier is None:
        return context.get_current()

    candidates: list[dict[str, Any]] = []

    if hasattr(carrier, "metadata") and isinstance(carrier.metadata, dict):
        candidates.append(carrier.metadata)

    if isinstance(carrier, dict):
        candidates.append(carrier)
        if "metadata" in carrier and isinstance(carrier["metadata"], dict):
            candidates.append(carrier["metadata"])

        # Inspect Redis Streams payload field
        if "payload" in carrier:
            raw = carrier["payload"]
            parsed: Any = None
            if isinstance(raw, str):
                with contextlib.suppress(Exception):
                    parsed = json.loads(raw)
            elif isinstance(raw, dict):
                parsed = raw

            if isinstance(parsed, dict):
                candidates.append(parsed)
                if "metadata" in parsed and isinstance(parsed["metadata"], dict):
                    candidates.append(parsed["metadata"])

    for candidate in candidates:
        extracted = _propagator.extract(candidate)
        span_ctx = trace.get_current_span(extracted).get_span_context()
        if span_ctx.is_valid:
            return extracted

    return _propagator.extract({})


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    ctx: Context | None = None,
    tracer_name: str = "runefoble",
) -> Generator[trace.Span]:
    """Context manager for tracing discrete blocks of execution."""
    tracer = get_tracer(tracer_name)
    with tracer.start_as_current_span(name, context=ctx, attributes=attributes or {}) as span:
        yield span


__all__ = [
    "init_telemetry",
    "instrument_fastapi",
    "uninstrument_fastapi",
    "reset_tracer_provider",
    "get_tracer",
    "inject_trace_context",
    "extract_trace_context",
    "trace_span",
]
