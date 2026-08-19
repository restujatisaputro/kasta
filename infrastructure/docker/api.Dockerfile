FROM ghcr.io/astral-sh/uv:0.12.5 AS uv

FROM python:3.14.6-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build
COPY --from=uv /uv /uvx /bin/
COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY apps/api/src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.14.6-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/kasta/bin:$PATH

RUN groupadd --system kasta && useradd --system --gid kasta --home-dir /opt/kasta kasta
WORKDIR /opt/kasta
COPY --from=builder --chown=kasta:kasta /build/.venv /opt/kasta
COPY --chown=kasta:kasta apps/api/alembic.ini ./alembic.ini
COPY --chown=kasta:kasta apps/api/migrations ./migrations

USER kasta
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=6 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live')"
CMD ["python", "-m", "uvicorn", "kasta_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
