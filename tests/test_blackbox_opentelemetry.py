"""Blackbox tests for OpenTelemetry distributed tracing, metrics, and trace propagation."""

from __future__ import annotations

import uuid

import pytest
from gateway_api.main import app as gateway_app
from gateway_api.main import set_event_bus
from httpx import ASGITransport, AsyncClient
from opentelemetry import trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from runefoble_events.events import TokenMoved
from runefoble_platform.config import PlatformSettings
from runefoble_platform.consumer_group import MockAsyncRedis, deserialize_event
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.telemetry import (
    extract_trace_context,
    init_telemetry,
    reset_tracer_provider,
    uninstrument_fastapi,
)


@pytest.fixture(autouse=True)
def clean_telemetry():
    """Ensure clean tracer provider and instrumentation before and after each test."""
    reset_tracer_provider()
    yield
    uninstrument_fastapi(gateway_app)
    reset_tracer_provider()


@pytest.mark.asyncio
async def test_blackbox_gateway_http_spans_emitted():
    """Exercise public frontdoor route and verify spans have service.name, http.route, and http.status_code."""
    memory_exporter = InMemorySpanExporter()
    settings = PlatformSettings(environment="test")

    init_telemetry(
        service_name="gateway-api",
        settings=settings,
        app=gateway_app,
        span_exporter=memory_exporter,
        force=True,
    )

    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    spans = memory_exporter.get_finished_spans()
    assert len(spans) > 0, "Expected at least one span to be emitted to in-memory exporter"

    # Locate the primary HTTP server span
    server_spans = [s for s in spans if s.attributes.get("http.route") == "/healthz"]
    assert len(server_spans) == 1, f"Expected 1 server span for /healthz, found {len(server_spans)}"

    server_span = server_spans[0]
    assert server_span.resource.attributes.get("service.name") == "gateway-api"
    assert server_span.attributes.get("http.route") == "/healthz"
    assert server_span.attributes.get("http.status_code") == 200


@pytest.mark.asyncio
async def test_blackbox_w3c_incoming_trace_propagation():
    """Verify incoming W3C traceparent headers are propagated into server spans."""
    memory_exporter = InMemorySpanExporter()
    settings = PlatformSettings(environment="test")

    init_telemetry(
        service_name="gateway-api",
        settings=settings,
        app=gateway_app,
        span_exporter=memory_exporter,
        force=True,
    )

    trace_id_hex = "4bf92f3577b34da6a3ce929d0e0e4736"
    span_id_hex = "00f067aa0ba902b7"
    incoming_traceparent = f"00-{trace_id_hex}-{span_id_hex}-01"

    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/healthz",
            headers={"traceparent": incoming_traceparent},
        )
        assert response.status_code == 200

    spans = memory_exporter.get_finished_spans()
    server_spans = [s for s in spans if s.attributes.get("http.route") == "/healthz"]
    assert len(server_spans) == 1

    server_span = server_spans[0]
    span_context = server_span.get_span_context()
    # Converted trace_id int should match the incoming hex
    assert format(span_context.trace_id, "032x") == trace_id_hex
    assert format(server_span.parent.span_id, "016x") == span_id_hex


@pytest.mark.asyncio
async def test_blackbox_trace_propagation_across_redis_streams():
    """Verify trace context injection into Redis Streams and child span extraction."""
    memory_exporter = InMemorySpanExporter()
    settings = PlatformSettings(environment="test")

    provider = init_telemetry(
        service_name="gateway-api",
        settings=settings,
        app=gateway_app,
        span_exporter=memory_exporter,
        force=True,
    )

    mock_redis = MockAsyncRedis()
    event_bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(event_bus)

    stream_name = "runefoble.events.spectator"

    # Execute request to spectator frontdoor endpoint that dispatches a domain event
    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/spectate/sess-trace-001")
        assert res.status_code == 200

    # Verify event was published to mock Redis stream
    assert stream_name in mock_redis.streams
    assert len(mock_redis.streams[stream_name]) == 1

    _msg_id, fields = mock_redis.streams[stream_name][0]
    assert "traceparent" in fields, "Stream entry fields must include injected traceparent"

    # Extract trace context and verify child span inherits parent trace ID
    extracted_ctx = extract_trace_context(fields)
    tracer = trace.get_tracer("test-consumer", tracer_provider=provider)

    with tracer.start_as_current_span(
        "process_spectator_event", context=extracted_ctx
    ) as child_span:
        child_trace_id = format(child_span.get_span_context().trace_id, "032x")

    spans = memory_exporter.get_finished_spans()
    server_spans = [
        s for s in spans if s.attributes.get("http.route") == "/api/v1/spectate/{session_id}"
    ]
    assert len(server_spans) == 1

    root_trace_id = format(server_spans[0].get_span_context().trace_id, "032x")
    assert child_trace_id == root_trace_id, "Child span must share trace ID with gateway HTTP span"


@pytest.mark.asyncio
async def test_blackbox_trace_injection_and_deserialization_roundtrip():
    """Verify inject_trace_context and extract_trace_context across DomainEvent roundtrips."""
    memory_exporter = InMemorySpanExporter()
    provider = init_telemetry(
        service_name="board-state",
        span_exporter=memory_exporter,
        force=True,
    )
    tracer = trace.get_tracer("test-board", tracer_provider=provider)

    mock_redis = MockAsyncRedis()
    event_bus = RedisStreamsEventBus(client=mock_redis)

    session_id = uuid.uuid4()
    stream = "runefoble.events.board"

    with tracer.start_as_current_span("player_move_intent") as parent_span:
        event = TokenMoved(
            aggregate_id=session_id,
            token_id="token-wizard",
            name="Gandalf",
            from_x=1,
            from_y=1,
            to_x=2,
            to_y=3,
        )
        await event_bus.publish_event(stream, event)

    _msg_id, stored_fields = mock_redis.streams[stream][0]
    assert "traceparent" in stored_fields

    # Deserialize back from fields
    deserialized = deserialize_event(stored_fields)
    assert isinstance(deserialized, TokenMoved)
    assert "traceparent" in deserialized.metadata

    # Verify extracted context matches original span
    extracted_ctx = extract_trace_context(deserialized)
    extracted_span = trace.get_current_span(extracted_ctx)
    assert extracted_span.get_span_context().trace_id == parent_span.get_span_context().trace_id
