"""The dependency container of one gateway MCP app (TASK-0746).

`server.build_mcp` builds one container per app and passes it to every tool, resource and
router. No module keeps a registry, client pool, or permission checker as a global. Each
test builds its own container, so two apps never share state.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.settings import load_spicedb_settings

from gateway_mcp.dynamic.registry import DynamicToolRegistry
from gateway_mcp.permissions import PermissionChecker, SpiceDBPermissionChecker
from gateway_mcp.service_clients import ServiceClientPool


@dataclass
class GatewayMcpContainer:
    """The state and ports that one gateway app uses."""

    registry: DynamicToolRegistry
    permissions: PermissionChecker
    service_clients: ServiceClientPool

    @classmethod
    def default(cls) -> GatewayMcpContainer:
        """Build the production wiring. The SpiceDB client is resolved on each use.

        Raises:
            ConfigurationError: The SpiceDB preshared key is missing (TASK-0720).
        """
        load_spicedb_settings()
        permissions = SpiceDBPermissionChecker(get_spicedb_client)
        return cls(
            registry=DynamicToolRegistry(permissions),
            permissions=permissions,
            service_clients=ServiceClientPool(),
        )


def bind_container(
    fn: Callable[..., Awaitable[Any]], container: GatewayMcpContainer
) -> Callable[..., Awaitable[Any]]:
    """Return `fn` with `container` bound as its first argument.

    FastMCP reads the signature, the name and the docstring of the returned callable. The
    container parameter is removed from the signature, so it never reaches the tool schema.
    """
    signature = inspect.signature(fn)
    parameters = list(signature.parameters.values())[1:]

    async def bound(*args: Any, **kwargs: Any) -> Any:
        return await fn(container, *args, **kwargs)

    bound.__signature__ = signature.replace(parameters=parameters)  # type: ignore[attr-defined]
    bound.__annotations__ = {k: v for k, v in fn.__annotations__.items() if k != "container"}
    bound.__name__ = fn.__name__
    bound.__doc__ = fn.__doc__
    return bound
