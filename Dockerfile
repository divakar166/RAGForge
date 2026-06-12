FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
# RUN uv sync --frozen --no-dev --group app --no-install-project
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_HTTP_TIMEOUT=300 \
    uv sync --frozen --no-dev --group app --no-install-project

COPY app/ ./app/
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/
RUN uv sync --frozen --no-dev --group app

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/app ./app
COPY --from=builder /app/alembic.ini ./alembic.ini
COPY --from=builder /app/alembic ./alembic
ENV PATH="/app/.venv/bin:$PATH"
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
