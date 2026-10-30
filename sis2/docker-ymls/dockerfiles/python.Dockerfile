FROM ghcr.io/astral-sh/uv:0.9.2-python3.12-trixie-slim AS build
ARG PACKAGE
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY shared shared
COPY services services
COPY infra/postgres infra/postgres
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package ${PACKAGE}

FROM python:3.12-slim-trixie
ARG SRC
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=build /app/.venv .venv
COPY ${SRC} .
USER nobody
