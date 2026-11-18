# Shared image for every Python uv-workspace service (ADR-0003, ADR-0005).
#
# Build one service with build args:
#   docker build -f deployments/docker/python-service.Dockerfile \
#     --build-arg SERVICE=game-session \
#     --build-arg APP=game_session.main:app \
#     --build-arg PORT=8004 \
#     -t runefoble/game-session:0.1.0 .
#
# SYSTEM_PACKAGES lists Debian packages to install before the app runs, for example
# `espeak-ng` for voice-agent. Leave it empty for services that need none.
#
# `make images` runs this build for every row of PYTHON_IMAGE_ROWS in the Makefile.

ARG PYTHON_VERSION=3.13
ARG UV_VERSION=0.12.21

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim

ARG SERVICE
ARG APP
ARG PORT=8000
ARG SYSTEM_PACKAGES=""

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/app/.venv/bin:$PATH \
    SERVICE_APP=${APP} \
    SERVICE_PORT=${PORT}

WORKDIR /app

RUN if [ -n "${SYSTEM_PACKAGES}" ]; then \
      apt-get update \
      && apt-get install -y --no-install-recommends ${SYSTEM_PACKAGES} \
      && rm -rf /var/lib/apt/lists/*; \
    fi

# The whole uv workspace is needed to resolve `uv.lock`. Tests and frontend code
# are excluded by .dockerignore. The install is editable, so a service finds its own source tree
# (for example services/<bc>/ui/manifest.json, which the service loads relative to its module).
COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package "${SERVICE}" --no-dev

RUN useradd --system --uid 10001 --no-create-home runefoble
USER runefoble

EXPOSE ${PORT}

# `sh -c` expands the APP and PORT variables. `exec` keeps uvicorn as PID 1.
CMD ["sh", "-c", "exec uvicorn \"$SERVICE_APP\" --host 0.0.0.0 --port \"$SERVICE_PORT\""]
