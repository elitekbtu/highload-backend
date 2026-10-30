# build context: sis2/ (docker build -f infra/postgres/Dockerfile .)
FROM ghcr.io/astral-sh/uv:0.9.2-python3.12-alpine AS build
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=shared,target=shared \
    --mount=type=bind,source=infra/postgres,target=infra/postgres \
    uv sync --frozen --no-dev --no-editable --package migrations

FROM python:3.12-alpine
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=build /app/.venv .venv
COPY infra/postgres/alembic.ini .
COPY infra/postgres/migrations migrations
USER nobody
CMD ["alembic", "upgrade", "head"]
