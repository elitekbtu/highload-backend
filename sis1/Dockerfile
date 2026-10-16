FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1
RUN pip install --no-cache-dir 'uv>=0.8,<1'
COPY pyproject.toml uv.lock ./

FROM base AS app
RUN uv sync --frozen --no-dev
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
RUN useradd --create-home app
USER app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

FROM base AS test
RUN uv sync --frozen
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
CMD ["pytest", "-q"]
