FROM mirror.gcr.io/library/python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/
RUN UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never uv sync --frozen --no-dev --no-cache

ENV PATH=/app/.venv/bin:$PATH \
    HOME=/tmp \
    BRAIN_HOST=0.0.0.0
USER 10001
EXPOSE 8790 8791
CMD ["python", "-m", "agentbrain"]
