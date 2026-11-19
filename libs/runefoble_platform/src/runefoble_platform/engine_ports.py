"""Shared mechanics for settings-selected engine ports.

A service declares a port (for example a transcriber or a map generator) in its own
bounded context. A settings value names the adapter. This module holds only the parts
that every port shares:

- `build_adapter` maps a settings value to a factory and fails with a clear message.
- `EngineUnavailableError` is the one error an adapter raises when its engine cannot
  produce a result. It is never replaced by a fallback value (ADR-0015).
- `engine_unavailable_handler` turns that error into HTTP 503.

Port interfaces stay in their owning service. Do not add domain methods here.
See docs/how-to/add-an-engine-port-adapter.md.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from fastapi import Request
from fastapi.responses import JSONResponse

from runefoble_platform.errors import ServiceUnavailableError


class UnknownAdapterError(ValueError):
    """A settings value names no registered adapter."""


class EngineUnavailableError(ServiceUnavailableError):
    """An adapter's engine cannot produce a result for the request.

    `error_code` is a stable snake_case identifier for clients, for example
    `speech_engine_unavailable`. `engine` names the adapter that failed. The body
    key for that name is `engine_field`. It is `engine` unless a published contract
    fixes another name, such as `generator` for the battlemap port.
    """

    def __init__(
        self,
        error_code: str,
        engine: str,
        message: str,
        *,
        engine_field: str = "engine",
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.engine = engine
        self.engine_field = engine_field

    def body(self) -> dict[str, str]:
        """Explicit error payload. It names the failure. It carries no substitute output."""
        return {
            "error": self.error_code,
            self.engine_field: self.engine,
            "message": str(self),
        }


def build_adapter[AdapterT](
    setting: str,
    value: str,
    registry: Mapping[str, Callable[[], AdapterT]],
) -> AdapterT:
    """Build the adapter that the settings value selects.

    Args:
        setting: The environment variable name, used in the error message.
        value: The configured value.
        registry: Allowed values mapped to zero-argument factories. Only the factory
            for `value` runs.

    Raises:
        UnknownAdapterError: `value` is not a key of `registry`. The message lists the
            allowed values.
    """
    factory = registry.get(value)
    if factory is None:
        allowed = ", ".join(f"'{name}'" for name in sorted(registry))
        raise UnknownAdapterError(f"{setting} is '{value}'. Allowed values: {allowed}.")
    return factory()


async def engine_unavailable_handler(request: Request, exc: EngineUnavailableError) -> JSONResponse:
    """Map an unavailable engine to HTTP 503. The body sits under `detail`, as FastAPI does."""
    return JSONResponse(status_code=503, content={"detail": exc.body()})
