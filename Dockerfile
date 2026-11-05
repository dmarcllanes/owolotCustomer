FROM ghcr.io/astral-sh/uv:0.13.7 AS uv

FROM python:3.12-slim

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY main.py ./
COPY static ./static
COPY assets ./assets

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
