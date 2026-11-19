"""Declarative table for pass-through proxy routes (TASK-0822, G-03).

A pass-through route forwards one request to one owner route and returns the reply. Such a route
needs no code of its own. A `ProxyRoute` row names the public path, the owner route, the body
mode, and the reply mode. The owner route is either its segments, or a function of
`runefoble_platform.service_client.owner_routes` (one definition of each owner path).
`register_proxy_routes` turns each row into a FastAPI route that calls `forward_json` or
`forward_bytes`.

Each generated endpoint carries a real signature: path parameters, query defaults, and the body
are declared to FastAPI. The OpenAPI document therefore lists them as before. The table does not
hold any check. A route that needs a check, a transform, or a second owner call stays a
hand-written route.

A segment that the owner path cannot encode (`.`, `..`, or an empty value) returns 404.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from gateway_api.auth import get_principal
from gateway_api.proxy import forward_bytes, forward_json
from pydantic import BaseModel
from runefoble_platform.service_client import OwnerRoute, path

_PATH_PARAM = re.compile(r"\{(\w+)\}")
_SEGMENT_PARAM = re.compile(r"^\{(\w+)\}$")

Method = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]


@dataclass(frozen=True)
class ProxyRoute:
    """One pass-through route.

    - `public_path`: the FastAPI path template, with `{name}` path parameters.
    - `owner_segments`: the owner path as segments. A segment `{name}` takes the path parameter.
      Empty when `owner` is set.
    - `owner`: a function of `owner_routes` that returns the owner route. Its parameters are the
      path parameters of `public_path`, by name.
    - `reply`: "json" returns the decoded JSON (`forward_json`); "bytes" relays the payload
      unchanged (`forward_bytes`).
    - `returns`: the return annotation the route declares. Binary routes use "response".
    - `body`: "none" sends no body. "raw" relays the request body as sent (`forward_bytes` only).
      "json" declares a JSON body to FastAPI: `body_model` when set, else any JSON value.
    - `query_all`: pass every query parameter of the request to the owner.
    - `query_defaults`: query parameters the route declares, as (name, default) pairs.
    - `principal`: require a verified caller (ADR-0015 c). The gateway checks the token only.
    """

    method: Method
    public_path: str
    owner_segments: tuple[str, ...]
    service: str
    name: str
    doc: str
    owner: Callable[..., OwnerRoute] | None = None
    reply: Literal["json", "bytes"] = "json"
    # The OpenAPI return type. "response" keeps a binary route's schema empty (`-> Response`).
    returns: Literal["any", "response"] = "any"
    body: Literal["none", "raw", "json"] = "none"
    body_model: type[BaseModel] | None = None
    query_all: bool = False
    query_defaults: tuple[tuple[str, str], ...] = ()
    principal: bool = False
    timeout: float = 5.0
    status_code: int | None = None

    def __post_init__(self) -> None:
        if self.reply == "bytes" and self.body == "json":
            raise ValueError(f"{self.name}: a bytes reply takes a raw or no body")
        if self.body == "raw" and self.reply == "json":
            raise ValueError(f"{self.name}: a raw body is forwarded with a bytes reply")
        if self.body_model is not None and self.body != "json":
            raise ValueError(f"{self.name}: body_model needs a json body")
        if self.query_all and self.query_defaults:
            raise ValueError(f"{self.name}: pick query_all or query_defaults, not both")
        template_params = set(_PATH_PARAM.findall(self.public_path))
        if (self.owner is None) == (not self.owner_segments):
            raise ValueError(f"{self.name}: give either owner_segments or owner")
        for segment in self.owner_segments:
            match = _SEGMENT_PARAM.match(segment)
            if match and match.group(1) not in template_params:
                raise ValueError(f"{self.name}: owner segment {segment} is not in the path")
        if self.owner is not None:
            owner_params = set(inspect.signature(self.owner).parameters)
            if owner_params != template_params:
                raise ValueError(f"{self.name}: owner takes {owner_params}, not {template_params}")

    def owner_path(self, values: dict[str, str]) -> str:
        """Build the owner path from the path parameter values.

        Raises ValueError when a value is one the owner path cannot encode.
        """
        if self.owner is not None:
            return self.owner(**values).path
        segments = [
            values[match.group(1)] if (match := _SEGMENT_PARAM.match(s)) else s
            for s in self.owner_segments
        ]
        return path(*segments)


def _owner_path(route: ProxyRoute, values: dict[str, str]) -> str:
    """Build the owner path. A segment the owner cannot encode is a missing resource."""
    try:
        return route.owner_path(values)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


def _build_endpoint(route: ProxyRoute) -> Callable[..., Awaitable[Any]]:
    """Return the endpoint of one row, with the signature that FastAPI reads."""
    path_params = _PATH_PARAM.findall(route.public_path)
    parameters = [
        inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
        *(
            inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, annotation=str)
            for name in path_params
        ),
        *(
            inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, annotation=str, default=value)
            for name, value in route.query_defaults
        ),
    ]
    if route.body == "json":
        annotation: Any = route.body_model or Annotated[Any, Body()]
        parameters.append(
            inspect.Parameter("body", inspect.Parameter.KEYWORD_ONLY, annotation=annotation)
        )

    async def endpoint(**kwargs: Any) -> Any:
        request: Request = kwargs["request"]
        owner = _owner_path(route, {name: kwargs[name] for name in path_params})
        params = _query_params(request, route, kwargs)
        timeout = route.timeout
        if route.reply == "bytes":
            return await forward_bytes(
                request,
                service=route.service,
                method=route.method,
                path=owner,
                params=params,
                timeout=timeout,
            )
        body = kwargs.get("body")
        if isinstance(body, BaseModel):
            body = body.model_dump(mode="json")
        return await forward_json(
            request,
            service=route.service,
            method=route.method,
            path=owner,
            json_body=body,
            params=params,
            timeout=timeout,
        )

    endpoint.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        parameters, return_annotation=Response if route.returns == "response" else Any
    )
    endpoint.__name__ = route.name
    endpoint.__qualname__ = route.name
    endpoint.__doc__ = route.doc
    return endpoint


def _query_params(
    request: Request, route: ProxyRoute, kwargs: dict[str, Any]
) -> dict[str, str] | None:
    if route.query_all:
        return dict(request.query_params)
    if route.query_defaults:
        return {name: kwargs[name] for name, _ in route.query_defaults}
    return None


def register_proxy_routes(router: APIRouter, routes: Sequence[ProxyRoute]) -> None:
    """Add one FastAPI route for each row. Call it once per router, at import time."""
    for route in routes:
        router.add_api_route(
            route.public_path,
            _build_endpoint(route),
            methods=[route.method],
            status_code=route.status_code,
            dependencies=[Depends(get_principal)] if route.principal else None,
        )
