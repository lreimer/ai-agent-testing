# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.7.2 /uv /usr/local/bin/uv
# uv installs the interpreter from .python-version and the locked environment
# outside the project directory; everything else uses `uv run --locked`.
ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    UV_PROJECT_ENVIRONMENT=/opt/uv/venv \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_LINK_MODE=copy
WORKDIR /app

FROM base AS deps
# Toolchain for native modules (better-sqlite3) without a prebuilt binary.
RUN apt-get update \
    && apt-get install -y --no-install-recommends make g++ \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_COMPILE_BYTECODE=1 uv sync --locked
COPY package.json package-lock.json .npmrc ./
RUN --mount=type=cache,target=/root/.npm \
    PYTHON="$(uv python find)" npm ci --no-audit --no-fund

FROM base
COPY --from=deps /opt/uv /opt/uv
COPY --from=deps /app/node_modules ./node_modules
COPY pyproject.toml uv.lock .python-version package.json pytest.ini ./
COPY evals ./evals
COPY tests ./tests

# The working directory must be writable for DeepEval and PromptFoo state files.
RUN chown 65532:65532 /app

ENV HOME=/tmp \
    UV_CACHE_DIR=/tmp/.cache/uv \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROMPTFOO_CONFIG_DIR=/tmp/.promptfoo \
    PROMPTFOO_DISABLE_TELEMETRY=1 \
    DEEPEVAL_TELEMETRY_OPT_OUT=YES \
    ADK_BASE_URL=http://ai-agent-testing:8000 \
    RUN_LIVE_EVALS=0
USER 65532:65532
CMD ["uv", "run", "--locked", "python", "-m", "pytest", "-v", "-rA", "-p", "no:cacheprovider"]
