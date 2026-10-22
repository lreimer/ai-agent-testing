# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS python-deps
COPY --from=ghcr.io/astral-sh/uv:0.7.2 /uv /bin/uv
WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

FROM node:24-bookworm-slim AS node-deps
# Toolchain for native modules (better-sqlite3) without a prebuilt binary.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 make g++ \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

FROM python:3.12-slim-bookworm
COPY --from=node-deps /usr/local/bin/node /usr/local/bin/node
WORKDIR /app

COPY --from=python-deps /app/.venv ./.venv
COPY --from=node-deps /app/node_modules ./node_modules
COPY package.json pyproject.toml pytest.ini ./
COPY evals ./evals
COPY tests ./tests

# The working directory must be writable for DeepEval and PromptFoo state files.
RUN chown 65532:65532 /app

ENV PATH="/app/.venv/bin:/app/node_modules/.bin:$PATH" \
    HOME=/tmp \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROMPTFOO_PYTHON=/app/.venv/bin/python \
    PROMPTFOO_CONFIG_DIR=/tmp/.promptfoo \
    PROMPTFOO_DISABLE_TELEMETRY=1 \
    DEEPEVAL_TELEMETRY_OPT_OUT=YES \
    ADK_BASE_URL=http://ai-agent-testing:8000 \
    RUN_LIVE_EVALS=0
USER 65532:65532
CMD ["python", "-m", "pytest", "-v", "-rA", "-p", "no:cacheprovider"]
