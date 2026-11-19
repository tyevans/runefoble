# How-To: Compose a Service with an App Container

## Overview

This guide shows how a service builds its repositories and clients at start-up, in one place, and gives them to its routes. ADR-0021 D6 sets the rules. `game_session` uses this pattern (TASK-0755). TASK-0859 moves `asset_forge`, `campaign_analytics`, `campaign_lore`, and `voice_agent` to it.

The rules:

- No module builds a repository, a client, or a service object at import time.
- No module has `get_` and `set_` globals for test injection.
- The app lifespan builds one frozen container and stores it on `app.state.container`.
- A required setting that is missing stops the service at start-up. It does not fail on the first request.

## Reference Layout

The paths are relative to `services/game_session/src/game_session/`.

| Module | Contents |
|---|---|
| `container.py` | `GameSessionContainer` and `build_container(settings, *, event_bus=None)` |
| `main.py` | `create_app(build=build_container)` and `app = create_app()` |
| `shared/container_access.py` | `app_container(conn)` and the `EventBus` dependency |
| `shared/child_index_queries.py` | The `ChildIndexes` dependency |
| `<package>/repositories.py` | One frozen dataclass of the package repositories, its `build_<package>_repositories()` function, and its `Depends` provider |

The packages are `campaign`, `play`, `downtime`, `settlement`, and `world` (ADR-0021 D1). The container holds one dataclass for each package.

## Step 1: Group the Repositories of One Package

Write one frozen dataclass, one build function, and one provider in `<package>/repositories.py`. The provider reads the container from the request or the WebSocket. It does not import `container.py`, so a domain package does not import the composition root.

```python
@dataclass(frozen=True)
class WorldRepositories:
    shared_worlds: AggregateRepository[SharedWorldAggregate]
    bounty_contracts: AggregateRepository[MercenaryBountyAggregate]


def build_world_repositories() -> WorldRepositories:
    return WorldRepositories(
        shared_worlds=create_aggregate_repository(SharedWorldAggregate),
        bounty_contracts=create_aggregate_repository(MercenaryBountyAggregate),
    )


def world_repositories(conn: HTTPConnection) -> WorldRepositories:
    return app_container(conn).world


WorldRepos = Annotated[WorldRepositories, Depends(world_repositories)]
```

Use `HTTPConnection` as the parameter type. FastAPI then resolves the provider for HTTP routes and for WebSocket routes.

## Step 2: Build the Container

`build_container` reads the settings once. It checks each required setting before it builds anything:

1. It loads the SpiceDB settings. A missing preshared key raises `ConfigurationError`.
2. In a deployed environment, it requires `RUNEFOBLE_WATCHER_URL`.
3. It builds the event store. A deployed service with an unreachable PostgreSQL store, or with the memory store, raises `EventStoreInitializationError` (ADR-0015 (f)).
4. It builds the event bus provider and every package dataclass.

The repositories do not hold the store. They resolve the process store on each operation, so a test that replaces the store reaches every route.

## Step 3: Build the Container in the Lifespan

`create_app(build)` passes `build` to the lifespan. The lifespan calls it, stores the result on `app.state.container`, connects the event bus, and starts the stream consumers with the container. At shutdown it stops the consumers and closes the bus.

```python
app = create_app()  # uvicorn serves game_session.main:app
```

A stream consumer gets the container part that it needs when the lifespan starts it, for example `start_audience_consumers(bus, container.play)`.

## Step 4: Use the Providers in Routes

Declare the providers as route parameters. Put them before any parameter that has a default value. Pass the repositories to helper functions as arguments. This route is in `routers/bounties.py`.

```python
@router.post("/{session_id}/contracts/bounties", status_code=201)
async def post_bounty(
    repos: WorldRepos,
    event_bus: EventBus,
    child_indexes: ChildIndexes,
    session_id: str,
    req: PostBountyRequest,
    caller_id: CallerId,
) -> dict[str, Any]:
    ...
    await repos.bounty_contracts.save(agg)
    if bus := event_bus.get():
        await publish_aggregate_events(bus, STREAM_SESSION, events)
    await link_child(child_indexes, SESSION_BOUNTIES, str(sid), str(bid))
```

Do not give a parameter of type `EventBus` the name of a local variable in the same function. The local value hides the provider.

## Step 5: Test Through a Test Container

Tests do not import `game_session.main:app`. They use the helpers in `tests/helpers/game_session_app.py`:

| Name | Use |
|---|---|
| `session_app` | The shared test app. Its container is the production container with the harness event bus provider. |
| `build_test_container()` | Build a new test container over the process event store. |
| `app_with_container(container)` | Make a new app that serves `container`, with or without its lifespan. |

To simulate a restart, build a new app with a new container over the same event store:

```python
restarted = TestClient(app_with_container(build_test_container()))
```

To simulate a store outage for one repository, copy the container with `dataclasses.replace`:

```python
container = session_app.state.container
outage = replace(container, downtime=replace(container.downtime, merchants=UnavailableRepository()))
client = TestClient(app_with_container(outage))
```

To check a start-up rule, run the real lifespan in a child process with `start_game_session(env_overrides, cwd)` from `tests/helpers/game_session_startup.py`. The tests are in `tests/test_blackbox_fail_loud_startup.py`.

## Related

- ADR-0021 D6: `docs/project/adrs/accepted/adr-0021-game-session-internal-bounded-contexts.md`
- [Test Cross-Service Calls with Live Upstreams](test-cross-service-calls-with-live-upstreams.md)
- [Redis Streams Event Bus](../reference/redis-streams-event-bus.md)
